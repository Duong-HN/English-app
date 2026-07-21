# Test plan

## Backend automated tests

- health endpoint returns `200`.
- reading analysis returns structured result.
- analysis is persisted and scoped to the user.
- empty/oversized input is rejected by validation.
- provider failure is returned as `502`, not an unhandled server error.

## Mobile tests

- empty text cannot be submitted.
- loading state disables the action.
- API result renders reading vocabulary and writing/speaking feedback.
- failed API request renders a user-readable error.
- history screen renders saved items and supports refresh.

## Manual acceptance test

Use 20 texts: signs, menus, short emails, a paragraph, a 100-word opinion, and five speaking transcripts. Record OCR quality, response time, invalid outputs, useful feedback and estimated API cost. Do not report AI scores as scientifically validated language-exam scores.
