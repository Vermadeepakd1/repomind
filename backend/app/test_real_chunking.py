from app.chunking import chunk_text


text = """const jwt = require("jsonwebtoken");
const User = require("../models/User");

const protect = async (req, res, next) => {
    let token;

    if (
        req.headers.authorization &&
        req.headers.authorization.startsWith("Bearer")
    ) {
        try {
            token = req.headers.authorization.split(" ")[1];

            const decoded = jwt.verify(
                token,
                process.env.JWT_SECRET
            );

            req.user = await User.findById(decoded.id)
                .select("-password");

            if (!req.user) {
                return res.status(401).json({
                    message: "User not found"
                });
            }

            return next();

        } catch (error) {
            console.error(error);

            res.status(401).json({
                message: "Not authorized, token failed"
            });
        }
    } else {
        return res.status(401).json({
            message: "Not authorized, no token"
        });
    }
};

module.exports = protect;
"""


chunks = chunk_text(
    text,
    chunk_size=300,
    overlap=50
)


for index, chunk in enumerate(chunks):

    print("\n==============================")
    print(f"CHUNK {index}")
    print(
        f"Lines: {chunk['start_line']} - "
        f"{chunk['end_line']}"
    )
    print("==============================")

    print(chunk["text"])