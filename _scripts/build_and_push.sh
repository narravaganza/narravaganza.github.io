set -ex
bundle exec jekyll build --destination docs
git add docs/
git commit -m $1
git push origin draft