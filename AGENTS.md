# Working agreement

- Read README.md, docs/specification.md, docs/implementation-plan.md and docs/stage-log.md before starting a stage.
- Implement the stage requested by the user; stop at its completion unless the user expands the scope.
- Keep docs/specification.md current in every stage. Distinguish implemented behavior, planned behavior, tested evidence and open dependencies. Append the stage's changes and validation to its history.
- Update docs/stage-log.md and the stage status in the implementation plan in the same change.
- Use the existing stage branch convention, focused commits and normal pushes. Do not force-push. Preserve unrelated user changes.
- Run the relevant checks listed in the README and report actual results. Never label mocks as live integrations or liveness as functional readiness.
- Keep secrets, private scan data, virtual environments, generated builds and model binaries out of Git.
- Do not start target scans as part of setup. Provider availability checks are read-only.
- Write project documentation, interface text, code comments and tests in English. Keep installation and usage in the root README and development milestones in docs/implementation-plan.md.
