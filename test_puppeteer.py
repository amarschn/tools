import urllib.request
import re

html = open("tools/rotor-balance/index.html").read()
print("Has form?", "id=\"calc-form\"" in html)
print("Has event listener?", "addEventListener(\"submit\"" in html)
print("Has preventDefault?", "event.preventDefault()" in html)
