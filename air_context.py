class Frame:
    def __init__(self):
        self.variables = dict()

    def register_var(self, name, value_type):
        if name in self.variables:
            raise RuntimeError("duplicate variable name `{}`".format(name))

        self.variables[name] = value_type


class Context:
    def __init__(self):
        self.frames = list()

    def pop_frame(self):
        assert len(self.frames) > 0
        self.frames.pop()

    def push_frame(self, frame):
        self.frames.append(frame)
