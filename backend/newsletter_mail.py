"""Newsletter content validation and safe HTML/plain-text rendering."""
import html
import json
import re
from urllib.parse import urlsplit

from fastapi import HTTPException


def email_address(value):
    if not isinstance(value, str):
        raise HTTPException(400, "Enter a valid email address.")
    value = value.strip().lower()
    if (len(value) > 254 or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9-]{2,63}", value)
            or len(value.split("@")[0]) > 64 or ".." in value.split("@")[0]
            or value.startswith(".") or ".@" in value):
        raise HTTPException(400, "Enter a valid email address.")
    return value


def text(value, maximum, label, required=False):
    if (not isinstance(value, str) or len(value.strip()) > maximum
            or any(ord(c) < 32 and c not in "\n\t" for c in value)
            or (required and not value.strip())):
        raise HTTPException(400, f"Check {label} (up to {maximum} characters).")
    return value.strip()


def url(value, required=False):
    value = text(value, 1000, "the link", required)
    if not value:
        return ""
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
    except ValueError:
        raise HTTPException(400, "Enter a valid HTTPS URL.") from None
    if parsed.scheme != "https" or not hostname or parsed.username or parsed.password or any(c.isspace() for c in value):
        raise HTTPException(400, "Images and links need a public HTTPS URL.")
    return value


def content_input(body):
    if not isinstance(body, dict):
        raise HTTPException(400, "Enter newsletter content.")
    result = {"title": text(body.get("title", ""), 120, "the draft name", True),
              "subject": text(body.get("subject", ""), 150, "the subject", True),
              "preheader": text(body.get("preheader", ""), 180, "the inbox preview")}
    if "\n" in result["subject"] or "\t" in result["subject"]:
        raise HTTPException(400, "The subject must fit on one line.")
    palette = body.get("palette", "confetti")
    if palette not in {"confetti", "cyan", "rose", "amber"}:
        raise HTTPException(400, "Choose a newsletter color palette.")
    result["palette"] = palette
    blocks = body.get("blocks", [])
    if not isinstance(blocks, list) or not 1 <= len(blocks) <= 12:
        raise HTTPException(400, "Add between one and 12 newsletter sections.")
    result["blocks"] = []
    for block in blocks:
        if not isinstance(block, dict) or block.get("kind") not in {"text", "image", "offer", "divider"}:
            raise HTTPException(400, "Choose a text, picture, offer or divider section.")
        kind = block["kind"]
        item = {"kind": kind}
        if kind == "divider":
            result["blocks"].append(item)
            continue
        item.update(heading=text(block.get("heading", ""), 120, "the section heading"),
                    body=text(block.get("body", ""), 2000, "the section text"),
                    image=url(block.get("image", ""), kind == "image"),
                    alt=text(block.get("alt", ""), 180, "the picture description"),
                    link=url(block.get("link", "")),
                    button=text(block.get("button", ""), 60, "the button label"),
                    badge=text(block.get("badge", ""), 50, "the offer badge"),
                    price=text(block.get("price", ""), 80, "the price line"))
        if kind in {"text", "offer"} and not (item["heading"] or item["body"] or item["image"]):
            raise HTTPException(400, "Add some content to each section.")
        if item["button"] and not item["link"]:
            raise HTTPException(400, "Add an HTTPS destination for the button.")
        result["blocks"].append(item)
    if len(json.dumps(result).encode()) > 60000:
        raise HTTPException(400, "This draft is too large. Shorten a section or use fewer sections.")
    return result


def render(content, settings, unsubscribe_url):
    esc = lambda value: html.escape(str(value), quote=True)
    colors = {"confetti": "#e94763", "cyan": "#007f9a", "rose": "#b92e62", "amber": "#976000"}
    accent = colors[content["palette"]]
    sections, plain = [], [content["subject"], content["preheader"], ""]
    for block in content["blocks"]:
        if block["kind"] == "divider":
            sections.append('<tr><td style="padding:12px 28px"><hr style="border:0;border-top:2px solid #e1d7c6"></td></tr>')
            plain.append("--------------------")
            continue
        cells = []
        if block["badge"]:
            cells.append(f'<p style="color:{accent};font-size:12px;font-weight:bold;letter-spacing:1px">{esc(block["badge"])}</p>')
        if block["image"]:
            image = f'<img src="{esc(block["image"])}" alt="{esc(block["alt"])}" width="544" style="display:block;width:100%;max-width:544px;height:auto;border:0;border-radius:8px">'
            cells.append(f'<a href="{esc(block["link"])}">{image}</a>' if block["link"] else image)
        if block["heading"]:
            cells.append(f'<h2 style="font-size:25px;line-height:1.25;margin:20px 0 12px">{esc(block["heading"])}</h2>')
        if block["body"]:
            cells.append('<p style="font-size:16px;line-height:1.7;margin:12px 0">' + esc(block["body"]).replace("\n", "<br>") + '</p>')
        if block["price"]:
            cells.append(f'<p style="font-size:22px;font-weight:bold">{esc(block["price"])}</p>')
        if block["link"] and block["button"]:
            cells.append(f'<p style="margin:24px 0"><a href="{esc(block["link"])}" style="background:{accent};color:#ffffff;text-decoration:none;padding:14px 20px;border-radius:5px;display:inline-block;font-weight:bold">{esc(block["button"])}</a></p>')
        sections.append('<tr><td style="padding:16px 28px">' + "".join(cells) + '</td></tr>')
        plain.extend([block["badge"], block["heading"], block["body"], block["alt"] if block["image"] else "", block["image"], block["price"], block["link"], ""])
    address = settings.get("postalAddress") or "[Add your business mailing address before sending]"
    footer = f'<p style="line-height:1.7">You opted in to RODDY news, advertising and occasional offers.<br>To leave the list, reply with “unsubscribe” or use the email link below.<br>{esc(address).replace(chr(10), "<br>")}</p><p><a href="{esc(unsubscribe_url)}" style="color:#444444">Email to unsubscribe</a> · <a href="https://roddy.world" style="color:#444444">Visit RODDY</a></p>'
    document = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(content["subject"])}</title></head><body style="margin:0;padding:24px 10px;background:#efede7;color:#171b1d;font-family:Arial,Helvetica,sans-serif"><div style="display:none;max-height:0;overflow:hidden">{esc(content["preheader"])}</div><table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center"><table role="presentation" width="600" cellspacing="0" cellpadding="0" style="width:100%;max-width:600px;background:#fff9ed;border-radius:12px;overflow:hidden"><tr><td style="height:9px;background:linear-gradient(90deg,#e94763,#f3ab36,#f8e651,#61c4bd,#5198d1,#a483ca)"></td></tr><tr><td style="padding:30px 28px 12px;font-size:31px;font-family:monospace;font-weight:bold">RODDY<span style="color:#d22630">●</span><p style="font:12px Arial,sans-serif;letter-spacing:2px;color:#555">A LITTLE SIGNAL FROM OUR CORNER OF THE WORLD.</p></td></tr>{"".join(sections)}<tr><td style="padding:24px 28px;font-size:12px;color:#555;border-top:1px solid #e1d7c6">{footer}</td></tr></table></td></tr></table></body></html>'''
    plain.extend(["You opted in to RODDY news, advertising and occasional offers. Reply with “unsubscribe” to leave the list.", address, "Unsubscribe: " + unsubscribe_url])
    return document, "\n".join(part for part in plain if part)
