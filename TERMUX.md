# pymtheg on Termux

## Prerequisites

- Termux  
  Links:
  [F-Droid](https://f-droid.org/packages/com.termux),
  [Google Play](https://play.google.com/store/apps/details?id=com.termux)

- Termux:API  
  Links:
  [F-Droid](https://f-droid.org/packages/com.termux.api),
  [Google Play](https://play.google.com/store/apps/details?id=com.termux.api)

Ensure that Termux has the permission to draw over other apps before proceeding. This
will allow the Termux URL Opener to properly function.

## Setup

### Quick Setup Script

Run the following command in the terminal:

(_This will take some time to complete, so come back after a while._)

```text
curl https://raw.githubusercontent.com/markjoshwel/pymtheg/main/termux-pymtheg-setup | sh
```

### Manual Setup

1. Install Python, ffmpeg and termux-api

   Firstly, upgrade your packages. This helps ensure that Python installs without a
   hitch.

   ```text
   pkg update
   ```

   Once updated, install the needed packages.

   ```text
   pkg install python ffmpeg termux-api
   ```

2. Install pymtheg

   Currently, only a certain version of rapidfuzz can be built on Android.
   ([maxbachmann/RapidFuzz#195](https://github.com/maxbachmann/RapidFuzz/issues/195))

   This will take some time to build, so hold the wakelock and enjoy a cup.

   ```text
   pip install rapidfuzz==1.91
   ```

   ```text
   pip install pymtheg
   ```

3. Setup Internal Storage

   By default, Termux does not have access to the internal storage. However, there is a
   command that allows us to gain access. Grant the permission when prompted.

   ```text
   termux-setup-storage
   ```

   Once complete, make a folder named pymtheg in your Movies folder located in your
   internal storage. This is where pymtheg will store the 15 second clips.

   ```text
   mkdir -p $HOME/storage/shared/Movies/pymtheg
   ```

4. Setup URL Opener

   Write the following into a file with the path `$HOME/bin/termux-url-opener`. You may
   have to create a directory called `bin` using the command `mkdir $HOME/bin`.

   ```shell
   #!/bin/sh

   # ensure pymtheg folder exists
   [ ! -d $HOME/storage/shared/Movies/pymtheg/ ] && mkdir -p $HOME/storage/shared/Movies/pymtheg
   # run pymtheg
   pymtheg $1 -d $HOME/storage/shared/Movies/pymtheg/ || exit &?
   # add clips to the android mediastore
   termux-media-scan $HOME/storage/movies/pymtheg/ -r
   ```

   Alternatively, run this command to obtain the script:

   ```text
   curl https://raw.githubusercontent.com/markjoshwel/pymtheg/main/termux-url-opener -o $HOME/bin/termux-url-opener
   ```

5. Enjoy!

   To use pymtheg, share a Spotify/YouTube link with Termux (keep note of the timestamps
   before you do so!) and select Termux in the share sheet. Let pymtheg do its magic, and
   share your newly created clip!
