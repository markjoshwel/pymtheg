# Changelog

## 2.3.2

Update READMEs to show new minimum Python version

## 2.3.1

Quality of use updates + minor code fixes/changes

- removed unused import
- add explanatory text for {cer} placeholder in --help
- added examples to pymtheg --help
- removed extra space in using defaults text, standardised usage of " for representing text in text
- reworked timestamp handling to ensure that e.g. `-cs "*" -ce "+15"` will always be `+15` seconds
- fix timestamp confirmation not appearing sometimes
- show song duration alongside song name
- 0 left strip confirmation timestamps/file name timestamps/song duration
- fix text formatting for invalid clip start/end messages during command line argument validation
- update spotdl to 3.9.4
- update rich to 12.2.0
- minimum python version is now 3.6.3


## 2.3.0

Changes to command line arguments, quality of use updates

- (possibly breaking) change behaviour of the `-o`, `--out` and `-d`, `--dir` arguments
  - `-o`, `--out` now specifies output file name rather than output file path
  - `-o`, `--out` and `-d`, `--dir` can be formatted
  - `-o`, `--out` complements `-d`, `--dir` argument rather than overrides it
- added `-e`, `--ext` to specify clip file extension
- added `-tf`, `--timestamp-format` to specify format of timestamp added to the end of clip path
- add timestamp confirmation for both random timestamps

See README or `pymtheg --help` for more information.

## 2.2.0

Quality of use update

- allow for start timestamp to be "*", where a random timestamp will be chosen
- show real timestamps during confirmation (e.g. "0:00 -> 0:15")
- bumped down minimum python dependency to 3.6.1

## 2.1.2

Quality of use update

- Fixed text formatting issues when displaying `[hh:mm:]ss`
- Fix "invalid link/query, nothing to do" when having a non-standard answer for overwrite prompt

## 2.1.0

Quality of use update

- Default timestamp confirmation prompt to `y`

## 2.0.2

Packaging fixes

- fix asciinema link in README

## 2.0.1

Bug fixes

- fixed a incorrectly placed newline
- removed a 10s pause used in debugging
- aligned statuses

## 2.0.0

Quality of use updates

- change `-cl`, `--clip-length` to `-ce`, `--clip-end`, with default `+15
- prompt user to confirm clip start and end after input
- prompt user if file already exists (unless `-o` was used)
- allow for relative timestamp of `-1` equal to song length
- added `-y`, `--yes` to agree to every y/n interaction
- added `-i`, `--image` to specify custom image
- status messages now have spinners (rich)

## 1.2.2

Bug fix + quality of use updates

- add `-cs`, `--clip-start` for specifying default clip start

- fix not visible by 2 errors

- only create output clip file if clip creation was successful

## 1.2.1

Minor change

- capture output for ffmpeg invocations except clip creation rather than use
  `-hide_banner -loglevel error` for better debugging

## 1.2.0

Quality of use + miscallaneous updates

- throw an error if `-o` argument is set to a directory

- re-query user if clip start timestamp transcends song duration

- add `-ffa`, `--ffargs` argument, allows passthrough of ffmpeg arguments for clip
  creation

- add `-ud`, `--use-defaults` argument, uses defaults of 0, +clip_length

- add `-hide_banner -loglevel error` to ffmpeg invocations to reduce terminal clutter

## 1.1.0

Instagram-friendly video output using AAC as output audio codec + usage improvements

- change output video ffmpeg arguments to support instagram uploads

- spotDL args split seperately from `invocate()`, allows for queries with spaces
  `e.g. pymtheg "sicko mode skrillex remix"`

- rewrote clip timestamp input loop

  Old:

  ```text
  pymtheg: info: enter the timestamp of clip start ([hh:mm:]ss)
    Travis Scott, Skrillex - SICKO MODE - Skrillex Remix: 0
  ```

  New:

  ```text
  pymtheg: info: enter timestamps in format [hh:mm:]ss
                 end timestamp can be relative, prefix with '+'
                 press enter to use given defaults
    Travis Scott, Skrillex - SICKO MODE - Skrillex Remix
      clip start: 0
        clip end: +15
  ```

## 1.0.1

Packaging fixes

## 1.0.0

Initial working release
