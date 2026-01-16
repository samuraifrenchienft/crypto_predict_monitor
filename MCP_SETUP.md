# MCP Server Setup Guide

## Prerequisites

### ⚠️ Node.js Required
Most MCP servers need Node.js. Install it first:

1. Download from: https://nodejs.org/ (LTS version recommended)
2. Run the installer
3. Restart your terminal/Windsurf after installation
4. Verify: `node --version` should show version number

---

## Pricing Summary

| Server | Cost | Requirements |
|--------|------|--------------|
| **Sequential Thinking** | ✅ FREE | Node.js (npx) |
| **Memory** | ✅ FREE | Node.js (npx) |
| **GitHub** | ✅ FREE | GitHub Personal Access Token (free) |
| **Fetch** | ✅ FREE | Node.js (npx) or Python (uvx) |
| **Time** | ✅ FREE | Node.js (npx) |
| **Git** | ✅ FREE | Already installed |

All servers are open source from Anthropic's official repository.

---

## Installation

### Step 1: Open Windsurf MCP Settings

1. Press `Ctrl+Shift+P` (Command Palette)
2. Type "MCP" and select **"Cascade: Open MCP Settings"**
3. This opens your `mcp_config.json` file

### Step 2: Add the Server Configurations

Add these to your `mcpServers` object in the config file:

```json
{
  "mcpServers": {
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git"]
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "fetch": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"]
    },
    "time": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-time"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<YOUR_TOKEN_HERE>"
      }
    }
  }
}
```

### Step 3: GitHub Token Setup (for GitHub MCP only)

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `read:org`, `read:user`
4. Copy the token and replace `<YOUR_TOKEN_HERE>` in the config

### Step 4: Restart Windsurf

After saving the config, restart Windsurf for changes to take effect.

---

## What Each Server Does

### Sequential Thinking (Recommended)
Enables structured, step-by-step reasoning for complex problems. Helps me:
- Break down complex debugging tasks
- Plan multi-step refactoring
- Analyze architectural decisions

### Memory
Persistent knowledge graph across sessions. Helps me:
- Remember project-specific patterns
- Track decisions made in previous sessions
- Build context about your codebase

### GitHub
Direct GitHub API access. Enables:
- Create/manage issues and PRs
- Search repositories
- Review code changes
- Manage releases

### Fetch
Web content fetching. Enables:
- Read API documentation
- Check market pages
- Fetch remote resources

### Time
Timezone handling. Useful for:
- Converting market timestamps
- Scheduling-related code
- Time-based calculations

---

## Verification

After setup, you can verify servers are working by asking me:
- "Use sequential thinking to analyze [problem]"
- "Remember that [fact] for this project"
- "Fetch the content from [URL]"
- "What time is it in UTC?"
- "Create a GitHub issue for [task]"

---

## Troubleshooting

### "npx not found"
Install Node.js from https://nodejs.org/

### "uvx not found"
Already installed! Run: `$env:Path = "C:\Users\AbuBa\.local\bin;$env:Path"`

### Server fails to start
Check Windsurf Output panel (View > Output > MCP) for error details.
