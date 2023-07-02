class Parsing:
    class Index:
        def Is(token: str):
            return token.isnumeric() and int(token) in range(1, 101)

        def Value(token: str):
            return int(token)

    def Top(tokens: list):
        arguments = dict()
        if tokens:
            if Parsing.Index.Is(tokens[-1]):
                arguments["index"] = Parsing.Index.Value(tokens.pop(-1))
            elif Parsing.Index.Is(tokens[0]):
                arguments["index"] = Parsing.Index.Value(tokens.pop(0))
            arguments["username"] = " ".join([token for token in tokens if token])
        return arguments
