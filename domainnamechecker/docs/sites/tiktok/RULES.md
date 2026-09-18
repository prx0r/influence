# TikTok — handle rules (official + observed)
Source: TikTok for Developers (creator oEmbed docs); oEmbed endpoint public.

## Acceptable names
- 2–24 chars, lowercase letters/numbers/period/underscore.

## Our method
- Structural oEmbed: `type==rich` + `author_url` ends `/@{u}` = TAKEN (high).
- Documented-missing shape → NOT_FOUND (medium; reactivation holds possible).
- `TIKTOK_COOKIE` passthrough for login-gated profiles; else UNKNOWN.
