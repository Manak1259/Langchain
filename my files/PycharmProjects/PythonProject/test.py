import jwt   # pip install pyjwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# 1. Generate RSA key pair
private_key_obj = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)

private_key = private_key_obj.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

public_key = private_key_obj.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

print("Private Key:\n", private_key.decode())
print("Public Key:\n", public_key.decode())

# 2. Create a JWT signed with private key
payload = {"sub": "1234567890", "name": "Manak Sahu", "admin": True}

token = jwt.encode(payload, private_key, algorithm="RS256")
print("\nJWT (RS256):\n", token)

# 3. Verify JWT with public key
decoded = jwt.decode(token, public_key, algorithms=["RS256"])
print("\nDecoded JWT:\n", decoded)
