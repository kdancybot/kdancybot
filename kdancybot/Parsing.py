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

    def Recent(tokens: list):
        arguments = dict()

        # set submitted only flag
        arguments["pass-only"] = False
        while "--pass-only" in tokens:
            arguments["pass-only"] = True
            tokens.remove("--pass-only")

        arguments.update(Parsing.Top(tokens))
        return arguments
