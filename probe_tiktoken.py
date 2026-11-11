import tiktoken
print("tiktoken", tiktoken.__version__, "from", tiktoken.__file__)
enc = tiktoken.get_encoding("gpt2")
print("gpt2 vocab size:", enc.n_vocab)
ids = enc.encode("Hello, world! こんにちは")
print("encode hello:", ids)
