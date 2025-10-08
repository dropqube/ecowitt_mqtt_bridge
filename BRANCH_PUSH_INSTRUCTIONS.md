# Recreating the Ecowitt MQTT Bridge Pull Request

The latest changes live on the `work` branch in this repository. To publish them with a fresh pull request on GitHub, follow these steps:

1. **Ensure you have the branch locally**
   ```bash
   git fetch origin
   git checkout work
   ```

2. **Push the branch to GitHub**
   ```bash
   git push origin work --force-with-lease
   ```

   *Use `--force-with-lease` to update the remote branch safely without overwriting any collaborator work.*

3. **Open a new pull request**
   * Navigate to the repository on GitHub.
   * Click **Compare & pull request** for the `work` branch.
   * Confirm the title and description, then submit the PR.

These steps will recreate the pull request with the current codebase, avoiding the prior branch mismatch.
