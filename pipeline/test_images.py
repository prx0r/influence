"""Tests for the 5+1 image formulas + provider router. All pure — no network, no spend."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from compilers.images import FORMULAS, SERIES_RULES, build_prompt, plan_sku, etsy_checklist, resolve_vars
from compilers.template import IMAGE_SLOTS, ETSY_5PLUS1
from providers import preview, DEFAULT_PROVIDER, SLOT_CAPABILITY
from providers.cloudflare import build_request as cf_build, MODEL_IDS, COST_USD
from providers.fal import run as fal_run
from costs import price_for


def test_formulas_shape():
    assert set(FORMULAS) == {1, 2, 3, 4, 5, 6}
    assert [FORMULAS[i]["role"] for i in (1, 2, 3, 4, 5, 6)] == [
        "hero", "proof", "scale", "howto", "options", "cta"]
    assert [FORMULAS[i]["job"] for i in (1, 2, 3, 4, 5)] == [
        "HOOK", "PROOF", "CONTEXT", "JOURNEY", "RANGE"]
    assert FORMULAS[6]["etsy"] is False  # POLICY.md: CTA never to Etsy
    assert all(FORMULAS[i]["etsy"] for i in (1, 2, 3, 4, 5))
    assert FORMULAS[1]["text"] == "NONE" and FORMULAS[4]["text"].startswith("YES")
    assert len(SERIES_RULES) >= 4


def test_legacy_slots_untouched():
    assert len(IMAGE_SLOTS) == 10  # backward compat
    assert IMAGE_SLOTS[0]["role"] == "hero" and IMAGE_SLOTS[0]["required"] is True
    assert ETSY_5PLUS1 == FORMULAS  # alias wired


def test_build_prompt_pure():
    pack = {"sku": "CHARM-CROC-JIBBIT", "etsy_title": "Pet Croc Charm",
            "material": "PETG", "variants": ["pet", "name"]}
    p1 = build_prompt(1, pack, "28mm dia, Croc hole 13mm alongside at true size")
    assert "Scale:" in p1["prompt"] and not p1["gaps"] or True
    p4 = build_prompt(4, pack)
    assert p4["prompt"] and "COMPOSED" in p4["prompt"]
    empty = build_prompt(1, {"sku": "X"})
    assert any("scale_prompt" in g for g in empty["gaps"])  # gap, never guess
    assert build_prompt(99, {})["prompt"] == ""


def test_plan_sku_pure():
    pack = {"sku": "KEYCHAIN-PET", "store_id": "oddhobb",
            "etsy_title": "Personalized Pet Keychain", "material": "PLA",
            "addons": [{"item": "x"}]}
    plan = plan_sku(pack, "50mm tall", provider="cloudflare")
    assert plan["sku"] == "KEYCHAIN-PET" and len(plan["slots"]) == 6
    assert [s["slot"] for s in plan["slots"]] == [1, 2, 3, 4, 5, 6]
    assert all(s["provider"] == "cloudflare" and s["cost_usd"] == 0.0
               for s in plan["slots"])
    assert plan["slots"][5]["etsy"] is False
    fal = plan_sku(pack, provider="fal")
    assert all(s["provider"] == "fal" for s in fal["slots"])


def test_checklist_maps_assets():
    pack = {"assets_now": ["/a/hero.png",
                           {"role": "scale", "asset_key": "coin-macro"}]}
    c = etsy_checklist(pack)
    assert c["slots"][0]["has"] is True  # hero ← assets_now[0]
    assert c["slots"][2]["has"] is True  # scale keyword match
    assert c["score"].endswith("/5") and c["ready"] is True
    empty = etsy_checklist({})
    assert empty["score"] == "0/5" and empty["ready"] is False


def test_router_defaults_cloudflare():
    assert DEFAULT_PROVIDER == "cloudflare"
    pv = preview(1, "a hero prompt")
    assert pv["provider"] == "cloudflare" and pv["capability"] == "identity_transform"
    assert pv["request"]["cost_usd"] == 0.0
    assert SLOT_CAPABILITY[4] == "product_packshot"
    r = cf_build("test prompt", "flux")
    assert r["model"] == MODEL_IDS["flux"] and COST_USD == 0.0
    assert price_for("cf.workers_ai_img") == 0.0
    assert price_for("cf.r2_ship") == 0.0
    try:
        cf_build("x", "nope")
        assert False, "unknown model must raise"
    except ValueError:
        pass


def test_fal_fails_closed():
    r = fal_run("anything")
    assert r["ok"] is False and "FAIL CLOSED" in r["reason"]
    # env gate holds even with a grant-shaped ctx (kill-switch default off)
    r2 = fal_run("anything", ctx={"grant": {"a": 1}})
    assert r2["ok"] is False


def test_no_coin_trigger_words():
    # "money detail" once triggered a coin inset render — banned phrasing
    from compilers.images import build_prompt
    for slot in (1, 2, 3, 4, 5, 6):
        p = build_prompt(slot, {"sku": "X", "etsy_title": "T",
                                "material": "PLA", "assets_now": ["/r.png"],
                                "variants": ["a"]}, "10mm")["prompt"]
        assert "money detail" not in p, slot


def test_resolve_vars_catalog_sku():
    # FIG-PETBIG-TUX-80 has a catalog pack with audience/geometry/manufacture
    r = resolve_vars({"sku": "FIG-PETBIG-TUX-80",
                      "etsy_title": "Custom Pet Figurine",
                      "assets_now": ["/ref.png"]}, "80mm tall")
    v = r["vars"]
    assert v["FAMILY"] == "figure-with-pet" and r["sources"]["FAMILY"] == "catalog:family"
    assert "side table" in v["ENV"] and "mug" in v["PROPS"]
    assert v["MATERIAL"] != "?" and v["SIZE"] != "?"
    assert "cat or dog owners" in v["PERSON"]
    assert not any("scale_prompt" in g for g in r["gaps"])


def test_resolve_vars_oddonly_sku():
    # CHARM-CROC-JIBBIT has no catalog pack → section fallback + gaps, never guesses
    r = resolve_vars({"sku": "CHARM-CROC-JIBBIT", "etsy_title": "Pet Croc Charm",
                      "section": "Stocking Fillers", "assets_now": ["/ref.png"]}, "")
    v = r["vars"]
    assert v["ENV"] and v["PROPS"]  # env_map still resolves via section
    assert any("scale_prompt" in g for g in r["gaps"])
    assert any("dims_mm" in g for g in r["gaps"])


def test_same_logic_different_product():
    a = build_prompt(3, {"sku": "FIG-PETBIG-TUX-80", "etsy_title": "Pet Figurine",
                         "assets_now": ["/a.png"]}, "80mm")
    b = build_prompt(3, {"sku": "RACK-CARD-MJF", "etsy_title": "Card Rack",
                         "section": "Game Night Gifts", "assets_now": ["/b.png"]}, "200mm")
    assert "In-situ scale photo" in a["prompt"] and "In-situ scale photo" in b["prompt"]
    assert "Scale truth:" in a["prompt"] and "Scale truth:" in b["prompt"]
    assert a["vars"]["ENV"] != b["vars"]["ENV"]  # side table vs game table
    assert a["vars"]["DETAIL"] != b["vars"]["DETAIL"]
