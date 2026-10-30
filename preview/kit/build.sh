set -e
python3 apply.py ../work.html preview.html ski_out.js >/dev/null
python3 ../waltski/scripts/build_public.py preview.html public_preview.html >/dev/null
