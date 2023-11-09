from kdancybot.api.osuAPIExtended import osuAPIExtended


class Parsing:
    # class Item:
    #     # def

    #     def Is(token: str):
    #         pass

    #     def Value(token: str):
    #         pass

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
                return 0000 < int(token) <= 5000000
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

    class Combo:
        def Is(token: str):
            try:
                return token[-1].lower() == "x" and int(token[:-1])
            except ValueError:
                return False

        def Value(token: str):
            return int(token[:-1])

    class Accuracy:
        def Is(token: str):
            try:
                return token[-1] == "%" and float(token[:-1])
            except ValueError:
                return False

        def Value(token: str):
            return float(token[:-1])

    class Misses:
        def Is(token: str):
            try:
                return token[-1].lower() == "m" and int(token[:-1])
            except ValueError:
                try:
                    return token[-2:].lower() == "xm" and int(token[:-2])
                except ValueError:
                    return False

        def Value(token: str):
            if token[-2].lower() == "x":
                return int(token[:-2])
            return int(token[:-1])

    def Profile(tokens: list, **kwargs):
        arguments = dict()
        if tokens:
            if Parsing.Username.Is(tokens):
                arguments["username"] = Parsing.Username.Value(tokens)
        return arguments

    def Top(tokens: list, **kwargs):
        arguments = dict()
        arguments["index"] = 1
        if tokens:
            if Parsing.Index.Is(tokens[-1]):
                arguments["index"] = Parsing.Index.Value(tokens.pop(-1))
            elif Parsing.Index.Is(tokens[0]):
                arguments["index"] = Parsing.Index.Value(tokens.pop(0))
            arguments["username"] = " ".join([token for token in tokens if token])
            if "username" not in arguments:
                arguments["username"] = kwargs.get("username")
        return arguments

    def Recent(tokens: list, **kwargs):
        arguments = dict()

        # set submitted only flag
        arguments["pass-only"] = False
        while "--pass-only" in tokens:
            arguments["pass-only"] = True
            tokens.remove("--pass-only")

        arguments.update(Parsing.Top(tokens, **kwargs))
        return arguments

    def Whatif(tokens: list, osu=None, **kwargs):
        arguments = dict()

        arguments["count"] = 1
        arguments["map_id"] = 0
        arguments["username"] = kwargs.get("username", "")

        # types ordered in size of sets
        # pp completely includes count, and map_id includes pp
        ordered_types = ["count", "pp", "map_id"]
        types = {
            "count": Parsing.Index,
            "pp": Parsing.PPValue,
            "map_id": Parsing.MapID,
        }
        for arg_type in ordered_types:
            for i in range(len(tokens)):
                if types[arg_type].Is(tokens[i]):
                    arguments[arg_type] = types[arg_type].Value(tokens[i])
                    tokens.pop(i)
                    break

        if Parsing.Username.Is(tokens):
            arguments["username"] = Parsing.Username.Value(tokens)

        # if `count` changed and `pp` is not set, it means value that should've went to `pp` went to `count`
        if arguments["count"] > 1 and not arguments.get("pp", ""):
            arguments["pp"] = arguments["count"]
            arguments["count"] = 1

        # if tokens:
        #     if "--recent-fc" in tokens and osu:
        #         tokens.remove("--recent-fc")
        #         recent_args = Parsing.Recent(tokens)
        #         recent_args["username"] = kwargs.get("username")
        #         arguments["recent"] = osu.recent(recent_args)
        #         arguments["map_id"] = arguments["recent"]["score_data"]["beatmap"]["id"]
        #         arguments["pp"] = osu.prepare_score_info(
        #             arguments["recent"]["score_data"]
        #         )["perf"].pp

        #     elif len(tokens) == 1:
        #         if Parsing.PPValue.Is(tokens[0]):
        #             arguments["pp"] = Parsing.PPValue.Value(tokens[0])

        #     else:
        #         for _ in range(2):
        #             if Parsing.PPValue.Is(tokens[0]):
        #                 arguments["pp"] = Parsing.PPValue.Value(tokens[0])
        #                 if Parsing.Count.Is(tokens[1]):
        #                     arguments["count"] = Parsing.Count.Value(tokens[1])
        #                 elif Parsing.MapID.Is(tokens[1]):
        #                     arguments["map_id"] = Parsing.MapID.Value(tokens[1])
        #                 elif Parsing.Username.Is(tokens[1:]):
        #                     arguments["username"] = Parsing.Username.Value(tokens[1:])
        #                 else:
        #                     tokens[0], tokens[1] = tokens[1], tokens[0]
        #                     continue
        #                 break
        #             else:
        #                 tokens[0], tokens[1] = tokens[1], tokens[0]
        #                 continue
        return arguments

    def PP(tokens: list, osu=None, **kwargs):
        recent = ["r", "-r", "recent", "--recent"]
        arguments = dict()
        if tokens:
            if any(x in recent for x in tokens) and osu:
                tokens = [x for x in tokens if x not in recent]
                recent_args = dict()
                recent_args["username"] = kwargs.get("username")
                arguments["recent"] = osu.recent(recent_args)
                arguments["map_id"] = arguments["recent"]["score_data"]["beatmap"]["id"]
                arguments["mods"] = arguments["recent"]["score_data"]
                # arguments["pp"] = osu.prepare_score_info(
                #     arguments["recent"]["score_data"]
                # )["perf"].pp
        pass
