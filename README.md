# upcata

**Cataclysm DDA updater tool for Linux and Mac OS X.**

This is a simple CLI script that will pull updates for [Cataclysm: Dark Days Ahead](https://cataclysmdda.org/), a complex rogue-like survival game. The game is constantly being updated, with experimental builds typically being released multiple times per day. This script will query the Cataclysm DDA GitHub project and check for new releases. A list of all changes/commits are shown since the last time you updated your local build.

## Installation

### Prerequsites
* Python 3.4+
* Arrow and Requests modules

### Install from git

```
git clone https://git.ycnrg.org/scm/gtool/upcata.git
cd upcata
sudo ./setup.py install
```

### Use without installation

Download the script into your base Cataclysm directory (explained further under Usage section)
```
pip3 install arrow requests
curl https://git.ycnrg.org/projects/GTOOL/repos/upcata/raw/upcata.py > upcata
chmod +x upcata
```

## Usage

Your files should be organized like below. The "base" directory in the example below is the `CatacylsmDDA` directory, which holds the various versions of Cataclysm that are installed, along with your save data and save backups.

```
+ ./CataclysmDDA
  +-- cataclysmdda-0.D-1234
  +-- cataclysmdda-0.D-6990
  +-- current --> cataclysmdda-0.D-6990
  +-- userdata
    +-- save
    +-- config
    +-- sound
```

The `userdata` directory should contain your `save`, `config`, and `sound` directories, which will be shared by all of your game versions. `current` is a symlink that points to the current version of the game. The updater will automatically download the tarball, extract it, add a version suffix, then update all of the symlinks. It will also create a backup of your save data, in case the new version somehow corrupts it.

## View Changes

To check for an update, and view changes (commit log messages) since the last version you've used, just run `upcata` from your Catacylsm base directory.

## Update

To install anew, or update to a new version, run the following command:
```
upcata -u
```

The script checks the symlink for `current` to determine your current local version. If the local version cannot be determined, the changelog will not be displayed.

Once the latest version is fetched, the tarball will be extracted (eg. to `cataclysmdda-0.D`), then renamed with the build suffix (eg. `cataclysmdda-0.D-3998`). Then, the `current` symlink is updated to point to the new version. The script then creates symlinks for the `save`, `config`, and `sound` directories in the new version directory to point to your global `userdata` directory. If your `userdata` directory does not exist, the script will create a new one for you. Once installation is complete, the script will backup your save data to `save-YYYYMMDD-HHMM`.

To run the game after update:
```
cd current
./cataclysmdda-tiles
```

