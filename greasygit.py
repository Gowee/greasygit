#!/usr/bin/env python3
from urllib.request import urlopen
from urllib.parse import unquote
from collections import namedtuple
import re
import subprocess
import os
import shlex


def get(url, data=None):
    with urlopen(url, None) as r:
        return r.read().decode("utf-8")


README_TEMPLATE = """\
# {name}
{description}

[Migrated from GreasyFork](https://greasyfork.org/scripts/{id}) 
with the help of [greasygit](https://github.com/Gowee/greasygit).
"""

Version = namedtuple("Version", ("number", "tag", "datetime", "message"))


class GreasyForkScript:
    """A script on Greasy Fork"""

    URL_BASE = "https://greasyfork.org"
    URL_SCRIPT_HOMEPAGE = URL_BASE + "/en/scripts/{id}"
    URL_HISTORY = URL_BASE + "/en/scripts/{id}/versions{suffix}"
    URL_CODE = URL_BASE + "/scripts/{id}/code/code.js?version={version}"
    REGEX_METADATA = r"<header>\s*<h2>(?P<name>[^<\n]+)</h2>\s*<p id=\"script-description\">(?P<description>[^<\n]+)</p>"
    REGEX_LINK_CANONICAL = r'<link rel="canonical" href="(?P<url>[^\"]+)">'
    REGEX_HISTORY = r"""
        <li>\s+<input[^\n]+\s+<input[^\n]+\s+ # leading unused content in <li>
            <a[^>]*\ href=\"/en/scripts/{id}[\w\-%+]+\?
            version=(?P<number>\d+)\">(?P<tag>[^<\"]+) # version number
            </a>\s+<time\ 
            datetime=\"(?P<datetime>[^\"]+) # datetime
            \"[^\n]+\s+
            -\ (?P<message>.+) # message
        \s+</li>
    """

    _versions = None

    def __init__(self, id: int):
        self.id = id
        self._load_metadata()

    def _load_metadata(self):
        d = get(self.URL_SCRIPT_HOMEPAGE.format(id=self.id))
        match = re.search(self.REGEX_METADATA, d)
        self.name = match.group("name")
        self.description = match.group("description")
        canon_url = re.search(self.REGEX_LINK_CANONICAL, d).group("url")
        self.simple_name = unquote(canon_url.split("/")[-1].lstrip(str(self.id) + "-"))

    def get_versions(self, all_versions=False):
        # if self._versions:
        #     return self._versions

        if all_versions:
            url_suffix = "?show_all_versions=1"
        else:
            url_suffix = ""
        d = get(self.URL_HISTORY.format(id=self.id, suffix=url_suffix))
        for version in re.finditer(
            self.REGEX_HISTORY.format(id=self.id), d, re.VERBOSE
        ):
            yield Version(
                version.group("number"),
                version.group("tag"),
                version.group("datetime"),
                version.group("message"),
            )

    def get_code(self, version):
        code = get(self.URL_CODE.format(id=self.id, version=version))
        return code


def execute_command(command, *args, **kwargs):
    kwargs["shell"] = True
    return subprocess.check_call(command, *args, **kwargs)


def write_file(path, content):
    with open(path, "wb") as f:
        return f.write(content.encode("utf-8"))


class GitRepo:
    def __init__(self, repo_name=None):
        self.path = (repo_name or ".") + "/"
        if repo_name:
            execute_command(f"git init {repo_name}")

    def update_and_add(self, file_path, content):
        write_file(self.path + file_path, content)
        self.add(file_path)

    def add(self, file_path):
        return execute_command(f"git add {file_path}", cwd=self.path)

    def commit(self, message, datetime=None, allowing_empty=False):
        envs = None
        if datetime:
            envs = os.environ.copy()
            envs.update({"GIT_AUTHOR_DATE": datetime, "GIT_COMMITTER_DATE": datetime})
        command = f"git commit -m {shlex.quote(message)}"
        if allowing_empty:
            command += " --allow-empty"
        execute_command(command, cwd=self.path, env=envs)

    def tag(self, name, message=None, annotated=False):
        command = f"git tag {name}"
        if message:
            command += f" -m {shlex.quote(message)}"
        if annotated:
            command += " -a"


def main():
    script_id = int(input("❓ Script ID: ").strip())
    all_versions = (
        input("❓ Include versions where code are not changed (Y/n): ").lower() != "n"
    )
    tagging = input("❓ Tag commits of every version ([Y/n): ").lower() != "n"
    # tagging_first = input("❓  (F/l): ").lower() != "n"

    print("📥 Fetching metadata...")
    gfscript = GreasyForkScript(script_id)
    print("ℹ️ Name:", gfscript.name)
    print("ℹ️ Description:", gfscript.description)

    repo_name = (
        input(f"❓ Repo name [{gfscript.simple_name}]: ").strip() or gfscript.simple_name
    )
    script_file_name = input(f"❓ Script file name [{repo_name}]: ").strip() or repo_name

    print("\n⚙️ Initializing git repo...")

    git = GitRepo(repo_name)

    git.update_and_add("README.md", README_TEMPLATE.format(**vars(gfscript)))
    git.commit("Init with greasygit")

    for version in reversed(list(gfscript.get_versions())):
        print(f"\n⚙️ Processing {version.tag} ({version.number})...")
        code = gfscript.get_code(version.number)
        git.update_and_add(script_file_name, code)
        git.commit(version.message, version.datetime, all_versions)
        if tagging:
            git.tag(version.tag)


if __name__ == "__main__":
    main()
