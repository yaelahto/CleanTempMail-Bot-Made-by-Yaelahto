"""
CleanTempMail Bot – cleantempmail.com
"""

import httpx
import json
import os
import re
import random
import string
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.rule import Rule
from rich.prompt import Prompt
from rich import box

BASE       = "https://cleantempmail.com"
SAVE_FILE  = "emails.json"
OTP_FILE   = "otp.txt"
MAX_EMAILS = 10
INTERVAL   = 5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "https://cleantempmail.com/",
    "Accept": "application/json",
}

console = Console(width=72)

OTP_PATTERN = re.compile(r"\b(\d{6})\b")


# ── persistence ────────────────────────────────────────────────────────────────

def load_emails() -> list[str]:
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE) as f:
            return json.load(f)
    return []


def save_emails(emails: list[str]):
    with open(SAVE_FILE, "w") as f:
        json.dump(emails, f)
    with open("Email.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(emails))


# ── api helpers ────────────────────────────────────────────────────────────────

def get_domains(client: httpx.Client) -> list[str]:
    r = client.get(f"{BASE}/api/domains", params={"limit": 2000})
    r.raise_for_status()
    data = r.json()
    if data.get("success"):
        return data["data"]["domains"]
    return []


def generate_email(client: httpx.Client, domain: str | None = None) -> str | None:
    """Minta server generate email baru. domain=None → server pilih random."""
    body = {"domain": domain} if domain else {}
    r = client.post(f"{BASE}/api/generate-email", json=body)
    r.raise_for_status()
    data = r.json()
    if data.get("success"):
        return data["data"]["email"]
    return None


def get_emails(client: httpx.Client, address: str) -> list[dict]:
    r = client.get(f"{BASE}/api/emails", params={"email": address})
    r.raise_for_status()
    data = r.json()
    if data.get("success"):
        return data["data"]["emails"]
    return []


def get_email_detail(client: httpx.Client, email_id: str) -> dict | None:
    try:
        r = client.get(f"{BASE}/api/email/{email_id}")
        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                return data.get("data", data)
    except Exception:
        pass
    return None


# ── OTP helpers ────────────────────────────────────────────────────────────────

def save_otp(otp_map: dict[str, list[str]], emails: list[str]):
    lines = []
    for address in emails:
        codes = otp_map.get(address, [])
        lines.append(f"{codes[0]}\n" if codes else "-\n")
    with open(OTP_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)


def scrape_codes(text: str) -> list[str]:
    if not text:
        return []
    seen = []
    for m in OTP_PATTERN.finditer(text):
        code = m.group(1)
        if code not in seen:
            seen.append(code)
    return seen


def display_codes(codes: list[str]):
    if not codes:
        console.print("  [dim]Tidak ada kode ditemukan.[/dim]")
        return
    body = Text()
    for i, code in enumerate(codes, 1):
        body.append(f"  {i}.  ", style="bold yellow")
        body.append(f"{code}\n", style="bold white")
    console.print(Panel(
        body,
        title="[bold yellow]🔑  Kode Ditemukan[/bold yellow]",
        border_style="yellow",
        box=box.ROUNDED,
        padding=(0, 2),
    ))


# ── domain picker ──────────────────────────────────────────────────────────────

def pick_domain(client: httpx.Client) -> str | None:
    """
    Tampilkan sub-menu pilih domain:
      R → random (server tentukan)
      S → cari & pilih manual dari daftar
    Kembalikan domain string atau None (random).
    """
    clear()
    header("Pilih Domain")

    menu_text = Text()
    menu_text.append("  R", style="bold cyan"); menu_text.append("  Random (server pilihkan)\n", style="white")
    menu_text.append("  S", style="bold cyan"); menu_text.append("  Pilih dari daftar domain\n", style="white")
    menu_text.append("  0", style="bold cyan"); menu_text.append("  Batal\n", style="white")
    console.print(Panel(menu_text, title="[white]Mode Domain[/white]",
                        border_style="white", box=box.ROUNDED, padding=(0, 2)))
    console.print()
    sub = Prompt.ask("  Pilih").strip().upper()

    if sub == "0":
        return "CANCEL"

    if sub == "R":
        return None  # None = random

    if sub == "S":
        info("Mengambil daftar domain…")
        domains = get_domains(client)
        if not domains:
            err("Gagal ambil domain.")
            time.sleep(1.2)
            return None

        # Filter/search
        console.print()
        keyword = Prompt.ask(
            f"  Cari domain [dim](Enter = tampil semua, {len(domains)} tersedia)[/dim]",
            default=""
        ).strip().lower()

        filtered = [d for d in domains if keyword in d] if keyword else domains
        if not filtered:
            warn("Tidak ada domain cocok.")
            time.sleep(1.2)
            return None

        # Tampil maksimal 50 pertama
        show = filtered[:50]
        console.print()
        body = Text()
        for i, d in enumerate(show, 1):
            body.append(f"  {i:>2}.", style="bold cyan")
            body.append(f"  {d}\n", style="white")
        if len(filtered) > 50:
            body.append(f"\n  [dim]…dan {len(filtered) - 50} lainnya. Perketat pencarian.[/dim]")
        console.print(Panel(body, title=f"[cyan]Domain Tersedia ({len(filtered)} cocok)[/cyan]",
                            border_style="cyan", box=box.ROUNDED, padding=(0, 1)))
        console.print()

        raw = Prompt.ask(f"  Nomor domain (1–{len(show)}) [dim]atau Enter = random[/dim]", default="").strip()
        if not raw:
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(show):
            return show[int(raw) - 1]
        else:
            err("Nomor tidak valid, pakai random.")
            time.sleep(0.8)
            return None

    # default
    return None


# ── ui helpers ─────────────────────────────────────────────────────────────────

def clear():
    console.clear()


def header(title: str):
    console.print()
    console.print(Rule(f"[bold cyan] {title} [/bold cyan]", style="cyan"))
    console.print()


def ok(msg: str):
    console.print(f"  [bold green]✓[/bold green]  {msg}")


def err(msg: str):
    console.print(f"  [bold red]✗[/bold red]  {msg}")


def warn(msg: str):
    console.print(f"  [bold yellow]![/bold yellow]  {msg}")


def info(msg: str):
    console.print(f"  [blue]i[/blue]  {msg}")


def pause():
    console.print()
    console.input("  [dim]Tekan Enter untuk kembali…[/dim]")


def divider():
    console.print(Rule(style="dim"))


def email_panel(emails: list[str]) -> Panel:
    if not emails:
        body = Text("  (belum ada email)", style="dim italic")
    else:
        body = Text()
        for i, e in enumerate(emails, 1):
            body.append(f"  {i}.  ", style="bold cyan")
            body.append(f"{e}\n", style="white")
    used = len(emails)
    title = f"[cyan]Email Tersimpan[/cyan]  [dim]({used}/{MAX_EMAILS})[/dim]"
    return Panel(body, title=title, border_style="cyan", box=box.ROUNDED, padding=(0, 1))


def inbox_table(msgs: list[dict], new_ids: set = set()) -> Table:
    t = Table(
        box=box.SIMPLE_HEAD,
        border_style="blue",
        header_style="bold cyan",
        show_lines=False,
        expand=True,
    )
    t.add_column("#",      style="dim",   width=3,  justify="right")
    t.add_column("Dari",   style="green", max_width=24)
    t.add_column("Subjek", style="white", max_width=30)
    t.add_column("Waktu",  style="dim",   max_width=14)
    t.add_column("",       width=5,       justify="center")

    for i, m in enumerate(msgs, 1):
        mid    = m.get("id", m.get("subject", str(i)))
        is_new = mid in new_ids
        badge  = "[bold green]NEW[/bold green]" if is_new else ""
        t.add_row(
            str(i),
            m.get("from", "-"),
            m.get("subject", "(no subject)"),
            m.get("date",  m.get("time", m.get("created_at", "-"))),
            badge,
        )
    return t


# ── features ───────────────────────────────────────────────────────────────────

def generate_emails_menu(client: httpx.Client, emails: list[str]) -> list[str]:
    clear()
    header("Generate Email Baru")
    slots = MAX_EMAILS - len(emails)
    if slots <= 0:
        warn(f"Sudah max {MAX_EMAILS} email. Reset dulu (menu 4).")
        time.sleep(1.2)
        return emails

    info(f"Slot tersedia: [bold]{slots}[/bold] dari [bold]{MAX_EMAILS}[/bold]")
    console.print()
    raw = Prompt.ask(f"  Jumlah email (1–{slots})", default="1")
    if not raw.isdigit() or not (1 <= int(raw) <= slots):
        err(f"Masukkan angka 1–{slots}.")
        time.sleep(1.2)
        return emails
    count = int(raw)

    # Tanya mode domain SEKALI untuk semua batch, atau per-email
    console.print()
    mode_text = Text()
    mode_text.append("  A", style="bold cyan"); mode_text.append("  Satu domain untuk semua email\n", style="white")
    mode_text.append("  B", style="bold cyan"); mode_text.append("  Pilih domain berbeda tiap email\n", style="white")
    mode_text.append("  R", style="bold cyan"); mode_text.append("  Random semua (cepat)\n", style="white")
    console.print(Panel(mode_text, title="[white]Mode Generasi[/white]",
                        border_style="white", box=box.ROUNDED, padding=(0, 2)))
    console.print()
    mode = Prompt.ask("  Pilih mode", default="R").strip().upper()

    # Tentukan domain shared (mode A)
    shared_domain: str | None = None
    if mode == "A":
        result = pick_domain(client)
        if result == "CANCEL":
            return emails
        shared_domain = result
        clear()
        header("Generate Email Baru")

    console.print()
    console.print(Rule("[dim]Generating…[/dim]", style="dim"))
    console.print()

    for n in range(1, count + 1):
        if mode == "B":
            # Per-email pick
            console.print(Rule(f"[dim]Email {n}/{count}[/dim]", style="dim"))
            result = pick_domain(client)
            if result == "CANCEL":
                info(f"Email {n} dibatalkan.")
                continue
            domain = result
            clear()
            header("Generate Email Baru")
            console.print()
            console.print(Rule("[dim]Generating…[/dim]", style="dim"))
            console.print()
        elif mode == "A":
            domain = shared_domain
        else:
            domain = None  # random

        try:
            address = generate_email(client, domain)
        except Exception as e:
            err(f"[{n}/{count}]  Gagal: {e}")
            continue

        if address:
            emails.append(address)
            ok(f"[{n}/{count}]  [bold cyan]{address}[/bold cyan]")
        else:
            err(f"[{n}/{count}]  Server tidak kembalikan email.")

    save_emails(emails)
    console.print()
    console.print(Panel(
        Align(f"[bold green]Selesai! Total email: {len(emails)} / {MAX_EMAILS}[/bold green]", "center"),
        border_style="green", box=box.ROUNDED, padding=(0, 2),
    ))
    pause()
    return emails


def _read_email_body(client: httpx.Client, msgs: list[dict], pick_str: str):
    """Tampilkan isi email + scrape kode otomatis."""
    idx = int(pick_str) - 1
    m   = msgs[idx]

    email_id = m.get("id")
    detail   = get_email_detail(client, email_id) if email_id else None
    if detail:
        m = detail

    body_raw = m.get("body", m.get("text", m.get("html", m.get("content", ""))))
    body_txt = re.sub(r"<[^>]+>", " ", str(body_raw))
    body_txt = re.sub(r"\s+", " ", body_txt).strip()

    meta = (
        f"[bold]Dari   :[/bold] [green]{m.get('from', '-')}[/green]\n"
        f"[bold]Subjek :[/bold] {m.get('subject', '(no subject)')}\n"
        f"[bold]Waktu  :[/bold] [dim]{m.get('date', m.get('time', m.get('created_at', '-')))}[/dim]\n"
        f"[dim]{'─' * 52}[/dim]\n"
        f"{body_txt[:2000]}"
    )
    console.print()
    console.print(Panel(
        meta,
        title=f"[bold cyan] ✉  Email #{pick_str} [/bold cyan]",
        border_style="blue", box=box.ROUNDED, padding=(1, 2),
    ))

    codes = scrape_codes(body_txt)
    if codes:
        with open(OTP_FILE, "a", encoding="utf-8") as f:
            f.writelines(f"{c}\n" for c in codes)
    console.print()
    display_codes(codes)


def _delete_selected_emails(emails: list[str]) -> list[str]:
    clear()
    header("Hapus Email Terpilih")
    if not emails:
        warn("Tidak ada email tersimpan.")
        pause()
        return emails

    body = Text()
    for i, e in enumerate(emails, 1):
        body.append(f"  {i}.  ", style="bold cyan")
        body.append(f"{e}\n", style="white")
    console.print(Panel(body, title="[cyan]Pilih Email yang Dihapus[/cyan]",
                        border_style="cyan", box=box.ROUNDED, padding=(0, 1)))
    console.print()
    info("Nomor dipisah koma, misal: 1,3,5  — Enter tanpa input = batal")
    console.print()

    raw = Prompt.ask("  Nomor email yang dihapus [dim](Enter = batal)[/dim]", default="").strip()
    if not raw:
        info("Dibatalkan.")
        time.sleep(0.8)
        return emails

    selected: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(emails):
            idx = int(part) - 1
            if idx not in selected:
                selected.append(idx)
        else:
            warn(f"Nomor tidak valid diabaikan: {part}")

    if not selected:
        err("Tidak ada nomor valid.")
        pause()
        return emails

    to_delete = [emails[i] for i in selected]
    body2 = Text()
    for e in to_delete:
        body2.append(f"  [red]•[/red]  {e}\n")
    console.print()
    console.print(Panel(body2, title=f"[red]{len(to_delete)} email akan dihapus[/red]",
                        border_style="red", box=box.ROUNDED, padding=(0, 1)))
    console.print()
    confirm = Prompt.ask("  Yakin hapus? [dim](y/N)[/dim]", default="N")
    if confirm.lower() != "y":
        info("Dibatalkan.")
        time.sleep(0.8)
        return emails

    emails = [e for e in emails if e not in to_delete]
    save_emails(emails)
    console.print()
    ok(f"[bold]{len(to_delete)} email dihapus. Sisa: {len(emails)} / {MAX_EMAILS}[/bold]")
    time.sleep(1)
    return emails


def add_old_email(client: httpx.Client, emails: list[str]) -> list[str]:
    clear()
    header("Tambah Email Lama / Kelola Email")

    while True:
        console.print(email_panel(emails))
        console.print()
        menu_text = Text()
        menu_text.append("  1", style="bold cyan"); menu_text.append("  Tambah email lama\n", style="white")
        menu_text.append("  2", style="bold cyan"); menu_text.append("  Hapus email terpilih\n", style="white")
        menu_text.append("  0", style="bold cyan"); menu_text.append("  Kembali\n", style="white")
        console.print(Panel(menu_text, title="[white]Sub-Menu[/white]",
                            border_style="white", box=box.ROUNDED, padding=(0, 2)))
        console.print()
        sub = Prompt.ask("  Pilih").strip()

        if sub == "0":
            break

        elif sub == "1":
            slots = MAX_EMAILS - len(emails)
            if slots <= 0:
                warn(f"Sudah max {MAX_EMAILS} email. Hapus dulu beberapa.")
                time.sleep(1.2)
                continue

            clear()
            header("Tambah Email Lama")
            info(f"Slot tersedia: [bold]{slots}[/bold] dari [bold]{MAX_EMAILS}[/bold]")
            info("Masukkan email lama satu per satu. Kosongkan untuk selesai.")
            console.print()

            added = 0
            while len(emails) < MAX_EMAILS:
                raw = Prompt.ask(f"  Email [{len(emails) + 1}/{MAX_EMAILS}] [dim](Enter = selesai)[/dim]", default="").strip()
                if not raw:
                    break
                if "@" not in raw or "." not in raw.split("@")[-1]:
                    err(f"Format tidak valid: {raw}")
                    continue
                if raw in emails:
                    warn(f"Sudah ada: {raw}")
                    continue
                # Cek inbox bisa diakses
                try:
                    msgs = get_emails(client, raw)
                    emails.append(raw)
                    ok(f"[bold cyan]{raw}[/bold cyan]  ditambahkan")
                    added += 1
                except Exception as e:
                    err(f"Gagal verifikasi inbox: {e}. Tambah tetap? [y/N]")
                    if Prompt.ask("", default="N").lower() == "y":
                        emails.append(raw)
                        ok(f"[bold cyan]{raw}[/bold cyan]  ditambahkan (tanpa verifikasi)")
                        added += 1

            if added:
                save_emails(emails)
                console.print()
                console.print(Panel(
                    Align(f"[bold green]{added} email ditambahkan. Total: {len(emails)} / {MAX_EMAILS}[/bold green]", "center"),
                    border_style="green", box=box.ROUNDED, padding=(0, 2),
                ))
            else:
                info("Tidak ada email yang ditambahkan.")
            pause()
            clear()
            header("Tambah Email Lama / Kelola Email")

        elif sub == "2":
            emails = _delete_selected_emails(emails)
            clear()
            header("Tambah Email Lama / Kelola Email")

        else:
            err("Pilihan tidak valid.")
            time.sleep(0.8)

    return emails


def check_inbox(client: httpx.Client, emails: list[str]):
    clear()
    header("Cek Inbox")
    if not emails:
        warn("Belum ada email. Generate dulu (menu 1).")
        pause()
        return

    body = "\n".join(
        [f"  [bold cyan]{i}[/bold cyan]  {e}" for i, e in enumerate(emails, 1)]
        + ["\n  [bold cyan]0[/bold cyan]  [dim]Cek semua sekaligus[/dim]"]
    )
    console.print(Panel(
        body,
        title="[cyan]Pilih Inbox[/cyan]",
        border_style="cyan", box=box.ROUNDED, padding=(0, 1),
    ))
    console.print()

    raw = Prompt.ask("  Nomor inbox")
    if not raw.isdigit():
        err("Input tidak valid.")
        pause()
        return

    idx     = int(raw)
    targets = emails if idx == 0 else ([emails[idx - 1]] if 1 <= idx <= len(emails) else [])
    if not targets:
        err("Nomor tidak valid.")
        pause()
        return

    for address in targets:
        console.print()
        console.print(Rule(f"[cyan]{address}[/cyan]", style="cyan"))
        try:
            msgs = get_emails(client, address)
        except Exception as e:
            err(f"Gagal ambil inbox: {e}")
            continue

        if not msgs:
            console.print(Align("[dim]📭  Inbox kosong[/dim]", "center"))
            continue

        console.print()
        console.print(inbox_table(msgs))
        console.print(f"\n  [dim]{len(msgs)} pesan[/dim]")
        console.print()

        pick = Prompt.ask("  Baca nomor pesan [dim](Enter = skip)[/dim]", default="")
        if pick.isdigit() and 1 <= int(pick) <= len(msgs):
            _read_email_body(client, msgs, pick)

    pause()


def scrape_codes_menu(client: httpx.Client, emails: list[str]):
    clear()
    header("Scrape Kode dari Inbox")
    if not emails:
        warn("Belum ada email. Generate dulu (menu 1).")
        pause()
        return

    info("Mengambil semua inbox dan mencari kode OTP 6 digit…")
    console.print()
    divider()

    otp_map: dict[str, list[str]] = {}
    any_found = False

    for address in emails:
        console.print()
        console.print(Rule(f"[cyan]{address}[/cyan]", style="cyan"))
        try:
            msgs = get_emails(client, address)
        except Exception as e:
            err(f"Gagal ambil inbox: {e}")
            otp_map[address] = []
            continue

        if not msgs:
            console.print("  [dim]📭  Inbox kosong[/dim]")
            otp_map[address] = []
            continue

        m        = msgs[0]
        email_id = m.get("id")
        detail   = get_email_detail(client, email_id) if email_id else None
        src      = detail if detail else m

        body_raw = src.get("body", src.get("text", src.get("html", src.get("content", ""))))
        body_txt = re.sub(r"<[^>]+>", " ", str(body_raw))
        body_txt = re.sub(r"\s+", " ", body_txt).strip()

        subj      = m.get("subject", "") + " " + body_txt
        all_codes = scrape_codes(subj)

        otp_map[address] = all_codes
        console.print(f"  [dim]{len(msgs)} pesan diperiksa[/dim]")
        display_codes(all_codes)
        if all_codes:
            any_found = True

    save_otp(otp_map, emails)

    console.print()
    divider()
    if any_found:
        ok(f"Disimpan ke [bold]{OTP_FILE}[/bold]  (urut sesuai email)")
    else:
        warn("Tidak ada kode 6 digit ditemukan di seluruh inbox.")

    pause()


def refresh_all_inbox(client: httpx.Client, emails: list[str]):
    clear()
    header("Auto Refresh Inbox")
    if not emails:
        warn("Belum ada email. Generate dulu (menu 1).")
        pause()
        return

    known: dict[str, set] = {e: set() for e in emails}
    cycle = 0

    console.print(Panel(
        f"  Memantau [bold cyan]{len(emails)}[/bold cyan] inbox"
        f"  •  refresh tiap [bold cyan]{INTERVAL}s[/bold cyan]\n"
        "  Baris [bold green]hijau[/bold green] = email baru"
        "  •  [bold red]Ctrl+C[/bold red] untuk berhenti",
        border_style="cyan", box=box.ROUNDED, padding=(0, 2),
    ))
    time.sleep(1)

    try:
        while True:
            cycle    += 1
            ts        = time.strftime("%H:%M:%S")
            new_total = 0
            sections  = []

            for address in emails:
                try:
                    msgs = get_emails(client, address)
                except Exception as e:
                    sections.append((address, None, str(e)))
                    continue

                cur_ids  = {m.get("id", m.get("subject", str(i))) for i, m in enumerate(msgs)}
                new_ids  = cur_ids - known[address]
                new_total += len(new_ids)
                known[address] = cur_ids
                sections.append((address, msgs, new_ids))

            clear()
            console.print(Panel(
                Align(
                    f"[bold cyan]Refresh #{cycle}[/bold cyan]"
                    f"  [dim]|[/dim]  {ts}"
                    f"  [dim]|[/dim]  [cyan]{INTERVAL}s[/cyan]"
                    f"  [dim]|[/dim]  [bold red]Ctrl+C[/bold red] stop",
                    "center",
                ),
                border_style="cyan", box=box.ROUNDED, padding=(0, 1),
            ))

            if new_total:
                console.print(Panel(
                    Align(f"[bold green]🔔  {new_total} email baru masuk![/bold green]", "center"),
                    border_style="green", box=box.ROUNDED,
                ))

            console.print()
            for address, msgs, extra in sections:
                console.print(Rule(f"[cyan]{address}[/cyan]", style="cyan"))
                if msgs is None:
                    err(f"Gagal: {extra}")
                elif not msgs:
                    console.print(Align("[dim]📭  Inbox kosong[/dim]", "center"))
                else:
                    console.print(inbox_table(msgs, extra))
                console.print()

            for remaining in range(INTERVAL, 0, -1):
                filled = "█" * (INTERVAL - remaining)
                empty  = "░" * remaining
                console.print(
                    f"\r  [dim]Berikutnya dalam [cyan]{remaining}s[/cyan]  {filled}{empty}[/dim]",
                    end="",
                )
                time.sleep(1)
            console.print()

    except KeyboardInterrupt:
        console.print()
        console.print(Panel(
            Align("[bold yellow]Auto Refresh dihentikan.[/bold yellow]", "center"),
            border_style="yellow", box=box.ROUNDED,
        ))
        time.sleep(0.8)


def reset_emails(emails: list[str]) -> list[str]:
    clear()
    header("Reset Semua Email")
    if not emails:
        warn("Tidak ada email tersimpan.")
        time.sleep(1)
        return emails

    body = "\n".join(f"  [red]•[/red]  {e}" for e in emails)
    console.print(Panel(
        body,
        title=f"[red]{len(emails)} email akan dihapus[/red]",
        border_style="red", box=box.ROUNDED, padding=(0, 1),
    ))
    console.print()
    confirm = Prompt.ask("  Yakin hapus semua? [dim](y/N)[/dim]", default="N")
    if confirm.lower() == "y":
        save_emails([])
        console.print()
        ok("[bold]Semua email berhasil dihapus.[/bold]")
        time.sleep(1)
        return []

    info("Dibatalkan.")
    time.sleep(0.8)
    return emails


# ── menu utama ─────────────────────────────────────────────────────────────────

MENU_ITEMS = [
    ("1", "Generate Email Baru"),
    ("2", "Tambah Email Lama"),
    ("3", "Cek Inbox"),
    ("4", "Scrape Kode dari Inbox"),
    ("5", "Auto Refresh Inbox"),
    ("6", "Reset Semua Email"),
    ("0", "Keluar"),
]


def show_menu(emails: list[str]):
    clear()

    console.print(Panel(
        Align(
            "[bold cyan]CLEANTEMPMAIL BOT[/bold cyan]\n"
            "[dim]cleantempmail.com • Temporary Email + Code Scraper[/dim]",
            "center",
        ),
        border_style="cyan", box=box.DOUBLE_EDGE, padding=(1, 6),
    ))
    console.print()

    console.print(email_panel(emails))
    console.print()

    menu_text = Text()
    for key, label in MENU_ITEMS:
        menu_text.append(f"  {key}", style="bold cyan")
        menu_text.append(f"  {label}\n", style="white")

    console.print(Panel(
        menu_text,
        title="[bold white]Menu[/bold white]",
        border_style="white", box=box.ROUNDED, padding=(0, 2),
    ))
    console.print()
    console.print(Align("[dim]by [bold cyan]Yaelahto[/bold cyan][/dim]", "center"))
    console.print()


def main():
    emails = load_emails()

    with httpx.Client(timeout=20, headers=HEADERS) as client:
        while True:
            show_menu(emails)
            choice = Prompt.ask("  [bold cyan]Pilih menu[/bold cyan]").strip()

            if choice == "1":
                emails = generate_emails_menu(client, emails)
            elif choice == "2":
                emails = add_old_email(client, emails)
            elif choice == "3":
                check_inbox(client, emails)
            elif choice == "4":
                scrape_codes_menu(client, emails)
            elif choice == "5":
                refresh_all_inbox(client, emails)
            elif choice == "6":
                emails = reset_emails(emails)
            elif choice == "0":
                clear()
                console.print(Panel(
                    Align("[bold cyan]Sampai jumpa![/bold cyan]", "center"),
                    border_style="cyan", box=box.ROUNDED, padding=(1, 4),
                ))
                break
            else:
                err("Pilihan tidak valid. Masukkan angka [cyan]0–6[/cyan].")
                time.sleep(1)


if __name__ == "__main__":
    main()
