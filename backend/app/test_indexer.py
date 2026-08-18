from app.indexer import index_repository


files = [
    {
        "path": "test_auth.js",
        "content": """const jwt = require("jsonwebtoken");

function authenticate(req, res, next) {
    const token = req.headers.authorization;

    if (!token) {
        return res.status(401).json({
            message: "No token"
        });
    }

    const decoded = jwt.verify(
        token,
        process.env.JWT_SECRET
    );

    req.user = decoded;

    next();
}
"""
    }
]


count = index_repository(
    files,
    repository_id="test-repository"
)

print("Indexed chunks:", count)