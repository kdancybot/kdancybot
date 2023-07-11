class Parsing:
    class Index:
        def Is(token: str):
            try:
                return 0 < int(token) <= 100
            except ValueError:
                return False

        def Value(token: str):
            return int(token)

    Count = Index

    class PPValue:
        def Is(token: str):
            try:
                return 0 <= float(token) < 2000
            except ValueError:
                return False

        def Value(token: str):
            return float(token)

    class MapID:
        def Is(token: str):
            try:
                return 2000 < int(token) <= 5000000
            except ValueError:
                return False

        def Value(token: str):
            return int(token)

    class Username:
        def Is(tokens: list):
            try:
                return len(" ".join([token for token in tokens if token])) <= 16
            except ValueError:
                return False

        def Value(tokens: list):
            return " ".join([token for token in tokens if token])

    def Profile(tokens: list):
        arguments = dict()
        if tokens:
            if Parsing.Username.Is(tokens):
                arguments['username'] = Parsing.Username.Value(tokens)
        return arguments

    def Top(tokens: list):
        arguments = dict()
        arguments["index"] = 1
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

    def Whatif(tokens: list):
        arguments = dict()

        arguments["count"] = 1
        arguments["map_id"] = 0

        if tokens and len(tokens) <= 2:
            if '--recent-fc' in tokens:
                arguments['map_id'] = 123
            if len(tokens) == 1 and Parsing.PPValue.Is(tokens[0]):
                arguments["pp"] = Parsing.PPValue.Value(tokens[0])
            else:
                for _ in range(2):
                    if Parsing.PPValue.Is(tokens[0]):
                        arguments["pp"] = Parsing.PPValue.Value(tokens[0])
                        if Parsing.Count.Is(tokens[1]):
                            arguments["count"] = Parsing.Count.Value(tokens[1])
                        elif Parsing.MapID.Is(tokens[1]):
                            arguments["map_id"] = Parsing.MapID.Value(tokens[1])
                        else:
                            tokens[0], tokens[1] = tokens[1], tokens[0]
                            continue
                        break
                    else:
                        tokens[0], tokens[1] = tokens[1], tokens[0]
                        continue
        return arguments
