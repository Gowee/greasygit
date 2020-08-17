# greasygit
greasygit helps migrate a script published on Greasy Fork to Git with history (commits) kept intact.  

## Run
```sh
python -V # Python version >= 3.6 should work well.
cd workspace # or other direcotry. greasygit will create a project directory there automatically.
curl -LO https://raw.githubusercontent.com/Gowee/greasygit/master/greasygit.py
chmod +x greasygit.py

./greasygit.py # Following the prompts to proceeed.

cd <REPO> && git log # Check the resulted commits.

git remote add <REMOTE> ... # Add a remote.
git push -u <REMOTE> <BRANCH>... # Push!
```
