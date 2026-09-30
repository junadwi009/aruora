"""Bounded user-editable fields; never identity, role, or verification fields."""
from __future__ import annotations
import re
import math
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from difflib import SequenceMatcher
from app.errors import ApiError

def invalid(message="Invalid profile fields"):
    raise ApiError("VALIDATION", message, 422)

def band(value):
    if isinstance(value, bool) or not isinstance(value, (int,float)):
        invalid("Band targets must be numeric half-band values")
    if not math.isfinite(value) or not 4 <= value <= 9 or value * 2 != int(value * 2):
        invalid("Band targets must be 4.0–9.0 in 0.5 steps")
    return float(value)

def profile_fields(raw):
    allowed={"name","country","bio","examDate","targetBand","skillTargets","reminderTime","reminderTz"}
    if not isinstance(raw,dict) or set(raw)-allowed:
        invalid()
    out={}
    for key,limit in (("name",120),("country",80),("bio",2000)):
        if key in raw:
            v=raw[key]
            if not isinstance(v,str) or len(v)>limit or (key=="name" and not v.strip()):invalid()
            out[key]=v.strip()
    if "examDate" in raw:
        value=raw["examDate"]
        if not isinstance(value,str):invalid("Exam date must be YYYY-MM-DD or empty")
        if value:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",value):invalid("Exam date must be YYYY-MM-DD")
            try:date.fromisoformat(value)
            except ValueError:invalid("Invalid exam date")
        out["examDate"]=value
    if "targetBand" in raw:out["targetBand"]=band(raw["targetBand"])
    if "skillTargets" in raw:
        vals=raw["skillTargets"]
        if not isinstance(vals,dict) or set(vals)-{"reading","listening","writing","speaking"}:invalid()
        out["skillTargets"]={k:band(v) for k,v in vals.items()}
    if "reminderTime" in raw:
        value=raw["reminderTime"]
        if value is not None and (not isinstance(value,str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):00",value)):
            invalid("Reminder time must be an hourly HH:00 slot or null")
        out["reminderTime"]=value
    if "reminderTz" in raw:
        value=raw["reminderTz"]
        if value is not None:
            if not isinstance(value,str) or not 1<=len(value)<=64:invalid("Invalid timezone")
            try:ZoneInfo(value)
            except (ValueError,ZoneInfoNotFoundError):invalid("Use a valid IANA timezone")
        out["reminderTz"]=value
    return out

def read_aloud_fields(raw):
    if not isinstance(raw,dict) or set(raw)-{"target","transcript"}:invalid("Send target and transcript only")
    for key,limit in (("target",240),("transcript",2400)):
        value=raw.get(key)
        if not isinstance(value,str) or not value.strip() or len(value)>limit:invalid("Invalid read-aloud text")
    return raw["target"].strip(),raw["transcript"].strip()

def word_evidence(target,transcript):
    # Text alignment is not phoneme/prosody assessment. Cap input before calling.
    tokenize=lambda t: re.findall(r"[\w']+",t.casefold())
    a,b=tokenize(target),tokenize(transcript)
    matched=set()
    for i,j,n in SequenceMatcher(None,a,b,autojunk=False).get_matching_blocks():
        matched.update(range(i,i+n))
    return {"accuracy":round(100*len(matched)/len(a),1) if a else 0.0,
            "missed":[v for i,v in enumerate(a) if i not in matched]}


def avatar_data(raw):
    import base64
    import binascii
    if not isinstance(raw, dict) or set(raw) != {"dataUrl"}:
        invalid("Expected one image data URL")
    value = raw["dataUrl"]
    if not isinstance(value, str) or len(value) > 2700000:
        invalid("Image exceeds 2 MB")
    match = re.fullmatch(r"data:image/(png|jpeg);base64,([A-Za-z0-9+/=]+)", value)
    if not match:
        invalid("Only base64 PNG and JPEG images are accepted")
    try:
        image = base64.b64decode(match[2], validate=True)
    except (ValueError, binascii.Error):
        invalid("Invalid image encoding")
    if not image or len(image) > 2000000:
        invalid("Image exceeds 2 MB")
    if not ((match[1] == "png" and image.startswith(b"\x89PNG\r\n\x1a\n"))
            or (match[1] == "jpeg" and image.startswith(b"\xff\xd8\xff"))):
        invalid("Image bytes do not match the declared format")
    return value


def authorize_google_link(account, provider_sub):
    """Do not elevate an attacker-precreated unverified local account by email linking."""
    if getattr(account, "email_verified", False) is not True:
        raise ApiError("GOOGLE_LINK_REQUIRES_RECOVERY", "Recover and verify the existing account before linking Google", 403)
    existing = getattr(account, "google_sub", None)
    if existing and existing != provider_sub:
        raise ApiError("GOOGLE_LINK_CONFLICT", "This account is linked to a different Google identity", 403)
