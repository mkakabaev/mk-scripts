# -*- coding: utf-8 -*-
# cSpell: words

# class Git(Runner):
#     def __init__(self, env, args):
#         super(Git, self).__init__(env, "git")
#         self.add_arg_pair2("--git-dir", env.git_root)
#         self.args += args

#     @property
#     def has_uncommitted_changes(self):
#         self.add_arg_pair2("--work-tree", self.env.git_root.subdirectory(".."))
#         self.add_arg("status")
#         self.add_arg("--porcelain")
#         result = self.run("Checking GIT status")
#         return result.strip() != ""

#     def commit(self, message):
#         self.add_arg_pair2("--work-tree", self.env.git_root.subdirectory(".."))
#         self.add_arg("commit")
#         self.add_arg("-a")
#         self.add_arg_pair("-m", "'{}'".format(message))
#         self.run("Committing to GIT")
