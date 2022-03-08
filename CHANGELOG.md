# Changelog

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
