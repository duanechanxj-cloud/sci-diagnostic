# V2.5.0 Testing

## Automated test suite

Run from the project root:

```bash
python -m pytest -q
```

Final build result: **66 passed**.

Coverage includes the retained V2.4.x workflow plus new V2.5.0 checks for:
- assessment-focused 82-LO curriculum master;
- 371-question TLG-strengthened bundled Candidate bank;
- validation of all 371 questions against the real 82-LO master;
- PBKDF2-SHA256 password hashing and authentication;
- single-user and multi-user secrets layouts;
- explicit question deletion and safe empty-bank schema;
- mutable-state ZIP snapshots excluding OAuth secrets/tokens and the static curriculum master;
- whole-app login contract;
- Deployment page and persistent-state hydration contract;
- Select All / Deselect All / Delete Selected / guarded Delete All UI;
- tablet-width responsive CSS contract.

## Packaging checks
The release should also pass:

```bash
python -m compileall -q app src scripts tests
```

and a fresh-unzip `python -m pytest -q` retest before distribution.
