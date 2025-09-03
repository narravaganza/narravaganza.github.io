set -ex
bundle exec jekyll build --destination docs

if [ "$1" == "-s" ]; then
    pkill -f "jekyll serve" || true
    bundle exec jekyll serve  \
        --livereload
fi
