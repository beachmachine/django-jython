# FIXME: Workaround for Jython defining an unusable SystemRandom:
import random
del random.SystemRandom
