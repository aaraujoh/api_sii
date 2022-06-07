from abc import ABC, abstractmethod

class DTEBase(ABC):
	@abstractmethod
	def dump(self):
		""" Devuelve la representación XML del objeto """
		return ""