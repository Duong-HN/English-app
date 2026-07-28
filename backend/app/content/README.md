# English A2→B1 content pack

`english_a2_b1.json` is the source of truth for the focused graduation-demo
course. It contains six original lessons in two units. The API imports the
pack into `courses`, `course_units` and `lessons` the first time the catalog is
requested.

The pack deliberately contains no copyrighted audio or video binaries. Three
lessons include a `media_plan` with an original recording script:

- `a2b1-changing-a-plan`
- `a2b1-polite-requests`
- `a2b1-solve-small-problem`

Record these scenes with the project team, add English captions, then upload
the files from the admin media screen. The upload metadata should use the
matching title and transcript from the JSON pack, `media_type=video`, and
`is_published=true` only after the recording has been reviewed.

The text, exercises and scripts are original MVP drafts. They are not an
official CEFR assessment or an IELTS preparation source. The provenance fields
are returned by the lesson API so the demo can show where each lesson came
from and what permission applies to it.
