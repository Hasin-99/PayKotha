from __future__ import annotations

import getpass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, FloatPrompt, Prompt
from rich.table import Table
from rich.text import Text

from src.models import User
from src.repositories.excel_store import ExcelStore
from src.services.payment_system import PaymentSystem
from src.utils.validators import format_money


console = Console()


class PayKothaCLI:
    """Industry-style interactive terminal for the wallet platform."""

    def __init__(self, data_dir: Path) -> None:
        self.system = PaymentSystem(ExcelStore(data_dir))
        self.session_user: User | None = None

    def run(self) -> None:
        self.system.load()
        self._banner()
        try:
            while True:
                if self.session_user is None:
                    if not self._guest_menu():
                        break
                else:
                    if not self._user_menu():
                        break
        finally:
            self.system.save()
            console.print("[bold green]Data saved to Excel. Goodbye![/bold green]")

    def _banner(self) -> None:
        stats = self.system.stats()
        console.print(
            Panel.fit(
                "[bold magenta]PayKotha[/bold magenta] — Mobile Payment System\n"
                "[dim]bKash-style wallet · Excel persistence · PIN security[/dim]\n"
                f"Users: {stats['users']}  ·  Transactions: {stats['transactions']}",
                border_style="magenta",
            )
        )

    def _guest_menu(self) -> bool:
        console.print(
            "\n[bold]1.[/] Register   [bold]2.[/] Login   [bold]3.[/] Admin snapshot   [bold]0.[/] Exit"
        )
        choice = Prompt.ask("Choose", choices=["0", "1", "2", "3"], default="2")
        try:
            if choice == "0":
                return False
            if choice == "1":
                self._register()
            elif choice == "2":
                self._login()
            elif choice == "3":
                self._admin_snapshot()
        except Exception as exc:
            console.print(f"[bold red]Error:[/] {exc}")
        return True

    def _user_menu(self) -> bool:
        assert self.session_user is not None
        u = self.session_user
        console.print(
            Panel(
                f"[bold]{u.name}[/]  ·  {u.phone_number}  ·  "
                f"Balance [bold green]{format_money(u.check_balance())}[/]",
                title="Session",
                border_style="cyan",
            )
        )
        console.print(
            "[bold]1.[/] Check Balance     [bold]2.[/] Cash In\n"
            "[bold]3.[/] Send Money        [bold]4.[/] Receive Money\n"
            "[bold]5.[/] Cash Out          [bold]6.[/] Transaction History\n"
            "[bold]7.[/] My Profile        [bold]8.[/] Logout\n"
            "[bold]0.[/] Save & Exit"
        )
        choice = Prompt.ask(
            "Choose",
            choices=["0", "1", "2", "3", "4", "5", "6", "7", "8"],
            default="1",
        )
        try:
            if choice == "0":
                return False
            if choice == "1":
                console.print(
                    f"[green]Current balance:[/] {format_money(u.check_balance())}"
                )
            elif choice == "2":
                self._cash_in()
            elif choice == "3":
                self._send()
            elif choice == "4":
                self._receive()
            elif choice == "5":
                self._cash_out()
            elif choice == "6":
                self._history()
            elif choice == "7":
                console.print(Panel(u.display_details(), title="Profile", border_style="blue"))
            elif choice == "8":
                self.session_user = None
                console.print("[yellow]Logged out.[/yellow]")
        except Exception as exc:
            console.print(f"[bold red]Error:[/] {exc}")
        return True

    def _register(self) -> None:
        console.print("[bold]Register new wallet[/bold]")
        name = Prompt.ask("Full name")
        phone = Prompt.ask("Phone (01XXXXXXXXX)")
        pin = getpass.getpass("Create PIN (4–6 digits): ")
        pin2 = getpass.getpass("Confirm PIN: ")
        if pin != pin2:
            raise ValueError("PINs do not match")
        opening = FloatPrompt.ask("Opening cash-in amount", default=0.0)
        user = self.system.register_user(name, phone, pin, opening_balance=opening)
        self.system.save()
        console.print(
            f"[bold green]Registered[/] {user.name} · ID {user.user_id} · "
            f"{format_money(user.check_balance())}"
        )
        if Confirm.ask("Login now?", default=True):
            self.session_user = user

    def _login(self) -> None:
        phone = Prompt.ask("Phone")
        pin = getpass.getpass("PIN: ")
        self.session_user = self.system.authenticate(phone, pin)
        console.print(f"[bold green]Welcome,[/] {self.session_user.name}!")

    def _cash_in(self) -> None:
        assert self.session_user
        amount = FloatPrompt.ask("Cash-in amount (৳)")
        txn = self.system.cash_in(self.session_user, amount)
        self.system.save()
        console.print(
            Panel(
                f"Cash-in successful\n{txn.display()}\n"
                f"New balance: {format_money(self.session_user.check_balance())}",
                border_style="green",
                title="Receipt",
            )
        )

    def _cash_out(self) -> None:
        assert self.session_user
        amount = FloatPrompt.ask("Cash-out amount (৳)")
        fee = round(amount * self.system.CASH_OUT_FEE_RATE, 2)
        console.print(f"Agent fee (~1.8%): {format_money(fee)} · Total debit: {format_money(amount + fee)}")
        if not Confirm.ask("Confirm cash-out?", default=True):
            return
        txn = self.system.cash_out(self.session_user, amount)
        self.system.save()
        console.print(
            Panel(
                f"Cash-out successful\n{txn.display()}\n"
                f"New balance: {format_money(self.session_user.check_balance())}",
                border_style="green",
                title="Receipt",
            )
        )

    def _send(self) -> None:
        assert self.session_user
        to_phone = Prompt.ask("Receiver phone")
        amount = FloatPrompt.ask("Amount (৳)")
        note = Prompt.ask("Note", default="P2P transfer")
        if not Confirm.ask(
            f"Send {format_money(amount)} to {to_phone}?", default=True
        ):
            return
        txn = self.system.send_money(self.session_user, to_phone, amount, note)
        self.system.save()
        console.print(
            Panel(
                f"Transfer successful\n{txn.display()}\n"
                f"New balance: {format_money(self.session_user.check_balance())}",
                border_style="green",
                title="Receipt",
            )
        )

    def _receive(self) -> None:
        """Pull funds from another account (spec: Receive Money)."""
        assert self.session_user
        from_phone = Prompt.ask("Sender phone")
        amount = FloatPrompt.ask("Amount (৳)")
        console.print(
            "[yellow]Note:[/] This debits the sender and credits you "
            "(demo of receive-flow). In production this would be a payment request."
        )
        if not Confirm.ask("Continue?", default=False):
            return
        # Need sender PIN in a real system — for course demo we authorize via current session
        # and document that production would require sender approval / OTP.
        sender = self.system.find_by_phone(from_phone)
        sender_pin = getpass.getpass(f"Enter PIN for sender {from_phone}: ")
        self.system.authenticate(from_phone, sender_pin)
        txn = self.system.send_money(sender, self.session_user.phone_number, amount, "Receive request")
        self.system.save()
        # refresh session user from store map
        self.session_user = self.system.get_user(self.session_user.user_id)
        console.print(
            Panel(
                f"Funds received\n{txn.display()}\n"
                f"New balance: {format_money(self.session_user.check_balance())}",
                border_style="green",
                title="Receipt",
            )
        )

    def _history(self) -> None:
        assert self.session_user
        rows = self.system.history_for(self.session_user)
        table = Table(title="Transaction History", show_lines=False)
        table.add_column("ID", style="cyan")
        table.add_column("Type")
        table.add_column("From → To")
        table.add_column("Amount", justify="right")
        table.add_column("Fee", justify="right")
        table.add_column("Date")
        if not rows:
            console.print("[dim]No transactions yet.[/dim]")
            return
        for t in rows:
            table.add_row(
                t.transaction_id,
                t.transaction_type.value,
                f"{t.sender_id} → {t.receiver_id}",
                format_money(t.amount),
                format_money(t.fee),
                t.date.strftime("%Y-%m-%d %H:%M"),
            )
        console.print(table)

    def _admin_snapshot(self) -> None:
        stats = self.system.stats()
        table = Table(title="Platform Snapshot")
        table.add_column("Metric")
        table.add_column("Value", justify="right")
        table.add_row("Registered users", str(stats["users"]))
        table.add_row("Transactions", str(stats["transactions"]))
        table.add_row("Gross volume", format_money(stats["total_volume"]))
        console.print(table)
        if self.system.users:
            users = Table(title="Users")
            users.add_column("ID")
            users.add_column("Name")
            users.add_column("Phone")
            users.add_column("Balance", justify="right")
            for u in self.system.users.values():
                users.add_row(u.user_id, u.name, u.phone_number, format_money(u.check_balance()))
            console.print(users)
