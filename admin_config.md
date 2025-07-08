# Admin Configuration

To set up admin access for the System Info page, create a `.env` file in the project root with the following variables:

```bash
# Admin Authentication
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password_here

# Flask Secret Key (required for sessions)
SECRET_KEY=your_flask_secret_key_here

# TAO Score Configuration
TAO_SCORE_COLUMN=tao_score_v21  # Options: tao_score_v21, tao_score (legacy)
```

## Default Credentials
If no `.env` file is found, the system will use these defaults:
- Username: `admin`
- Password: `tao2024`
- TAO Score Column: `tao_score_v21`

## TAO Score Configuration
The system uses a configurable TAO score column that can be set by admin:

- `tao_score_v21` (default): Latest TAO score algorithm
- `tao_score`: Legacy TAO score algorithm

**Important**: The system will never fall back to the old TAO score. Only the configured column will be used.

## Security Notes
- Change the default password immediately
- Use a strong, unique password
- Keep your `.env` file secure and never commit it to version control
- The `.env` file is already in `.gitignore` for security 