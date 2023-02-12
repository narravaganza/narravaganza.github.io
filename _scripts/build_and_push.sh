set -ex
bundle exec jekyll build --destination docs
git add docs/
git commit -m 'generate into docs'
git push origin draft