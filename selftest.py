#!/usr/bin/env python3
"""RingkasBot selftest — summarizer quality gates + credit ledger rules."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from summarizer import summarize, looks_like_url
from store import Store, FREE_TRIAL

passed = failed = 0


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        print("FAIL:", name)


ARTICLE = """The city council announced on Tuesday that the new public library will open
next spring after two years of construction. The building covers twelve thousand square
meters and holds reading rooms, a children's section, and a small theatre. Officials said
the library will lend books, host free classes, and provide computers for residents who
have no internet at home. The project cost forty million dollars, funded by the city and
private donors. Local teachers welcomed the plan, saying students need quiet places to
study after school. The mayor said the library is the first of three cultural buildings
planned for the district. A cafe and a garden will operate on the ground floor. Membership
will be free for all residents, and the library will open seven days a week. Critics asked
whether digital books make large libraries unnecessary, but the council argued that the
building is a community space, not only a book store. Registration for the first classes
begins in January."""

s = summarize(ARTICLE, max_sentences=3)
check("summary shorter than source", 0 < len(s) < len(ARTICLE) * 0.6)
check("summary keeps key fact (library)", "library" in s.lower())
check("short text passes through", summarize("One short sentence here.") == "One short sentence here.")
check("url detection", looks_like_url("https://example.com/a") and not looks_like_url("hello world"))

with tempfile.TemporaryDirectory() as d:
    st = Store(os.path.join(d, "t.db"))
    uid = 42
    b = st.balance(uid)
    check("new user gets free trial", b["free_left"] == FREE_TRIAL and b["credits"] == 0)
    for _ in range(FREE_TRIAL):
        check("free charge works", st.charge(uid) == "free")
    check("trial exhausted blocks charge", st.charge(uid) is None and not st.can_afford(uid))
    check("payment credits once", st.add_payment(uid, "charge-1", 10, 15) is True)
    check("duplicate charge id rejected", st.add_payment(uid, "charge-1", 10, 15) is False)
    check("balance after payment", st.balance(uid)["credits"] == 10)
    check("paid charge works", st.charge(uid) == "credit")
    check("credits decrease", st.balance(uid)["credits"] == 9)
    stats = st.stats()
    check("stats count stars", stats["stars_earned"] == 15 and stats["users"] == 1)

print(f"selftest: {passed} passed, {failed} failed")
raise SystemExit(1 if failed else 0)
