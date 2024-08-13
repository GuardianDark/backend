class CryptoServer:
    def __init__(self, key: int) -> None:
        self.key = key
        self.keyReal = 1
        if self.key != self.keyReal:
            raise ValueError('Invalid key')

    def encrypt(self, data):
        encrypted = ''.join(chr((ord(char) + self.key) % 256) for char in data)
        return encrypted

    def decrypt(self, data):
        decrypted = ''.join(chr((ord(char) - self.key) % 256) for char in data)
        return decrypted
