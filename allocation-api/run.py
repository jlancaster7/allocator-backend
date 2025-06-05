"""Flask application entry point"""

import os
from app.create_app import create_app
from app.core.config import settings

app = create_app()

if __name__ == "__main__":
    # Run the application
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=settings.DEBUG
    )