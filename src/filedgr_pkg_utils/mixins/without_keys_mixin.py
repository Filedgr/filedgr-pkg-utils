from typing import Dict, List


class WithoutKeysMixin:

    def without_keys(self, dictionary: Dict, exclude: List[str]) -> Dict:
        return {x: dictionary[x] for x in dictionary if x not in exclude}
