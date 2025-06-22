# Admin Configuration

To set up admin access for the System Info page, create a `.env` file in the project root with the following variables:

```bash
# Admin Authentication
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password_here

# Flask Secret Key (required for sessions)
SECRET_KEY=your_flask_secret_key_here
```

## Default Credentials
If no `.env` file is found, the system will use these defaults:
- Username: `admin`
- Password: `tao2024`

## Security Notes
- Change the default password immediately
- Use a strong, unique password
- Keep your `.env` file secure and never commit it to version control
- The `.env` file is already in `.gitignore` for security 