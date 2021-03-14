
class Species:

    __all_species = []

    def __init__(self, traits, ancestor=None):

        self.__name = Species.__getName()
        self.__traits = traits
        self.__ancestor = ancestor

        Species.__all_species.append(self)

    @property
    def name(self):
        return self.__name

    @staticmethod
    def __getName():

        name = ''
        i = len(Species.__all_species)

        first_letter_val = ord('A')
        interval_size = ord('Z') - first_letter_val + 1
        while i >= interval_size:

            name = chr(first_letter_val + i%interval_size) + name

            i //= interval_size
            i -= 1

        return chr(first_letter_val + i) + name

    def getChildSpecies(self, traits_config, traits):

        similarity = 0

        for trait in traits_config:
            parent_val = self.__traits.get(trait.name)
            child_val = traits.get(trait.name)

            similarity += trait.valuesSimilarity(
                parent_val, child_val)/len(traits_config)

            if similarity > 0.8:
                return self

        return Species(traits, ancestor=self)

    @staticmethod
    def searchByName(name):
        for species in Species.__all_species:
            if species.name == name:
                return species

        return None

    @staticmethod
    def loadFromDict(info):

        species = Species(info.get('traits'),
                          Species.searchByName(info.get('ancestor')))

        species.__name = info.get('name', 'UNKNOWN')

        return species

    def toDict(self):
        return {
            'name': self.__name,
            'traits': self.__traits,
            'ancestor': (None if self.__ancestor is None
                         else self.__ancestor.name)
        }

    @staticmethod
    def getAllSpecies():
        return iter(Species.__all_species)
