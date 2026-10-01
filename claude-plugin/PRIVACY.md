# Privacy Policy

Last updated: 2026-10-01. This policy covers the Articulate Writing plugin for
local Claude Code and Codex hosts. It is also published at
https://github.com/HarperZ9/articulate/blob/release/0.5.x/claude-plugin/PRIVACY.md.

**Data collected.** The plugin reads the text the calling host passes to one of
its tools, the events the host passes to its hooks (a session start, a file
edit, and the end of a reply), its own house-voice spec, and your house-voice
settings file. When you name a voice profile in `voice_compare`,
`voice_apply_plan` or `interview`, it reads that one profile and the store's
`identity.json` from the local voice store. It does not open your other files
or read conversation history or saved memory. It collects no account details,
usage statistics or telemetry.

**Use and storage.** The plugin checks text, applies the house voice and
prepares or validates host edits in memory on your computer, then returns the
result to the host. It writes no log, cache or copy of the text to disk. At
session start it adds the house-voice brief to the model's context; the brief
is the same published text for everyone and holds nothing about you. A voice
profile is made only by the command line (`articulate voice learn --mine`)
from files you name. It holds measured aggregates, never a sentence of your
samples, stays on your computer, and `articulate voice delete --all` removes
every profile, the identity file and the store folder. During
`voice_apply_plan` the profile's plain-sentence description enters the host
conversation, because the host model writes the rewrite.

**Third-party sharing.** The plugin opens no network connection and starts no
other program. The calling host already has the text in the conversation and
may send it to its model provider, together with the house-voice brief and,
during `voice_apply_plan`, your profile's description. That provider's privacy
policy and your account settings govern the conversation and tool results. No
second model account is needed by the plugin.

**Retention.** The plugin writes no persistent copy of the text, log or cache.
Request and response text can remain in process memory during the server session.
Voice profiles stay in your local voice store until you delete them. The host
may retain conversation text and tool results locally or remotely; its settings
and provider terms govern those copies.

**Contact.** Ask a question about this policy or the plugin at
https://github.com/HarperZ9/articulate/issues. Report a security problem
privately through the repository's security advisory reporting page.

**Changes.** A change to this policy ships in a new plugin version with a new
date above, and the changelog at
https://github.com/HarperZ9/articulate/blob/release/0.5.x/CHANGELOG.md lists it.
