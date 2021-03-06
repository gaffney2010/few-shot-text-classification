import attr
from typing import List

import pandas as pd
import warnings

from fewshot.embeddings.transformer_embeddings import (
    load_transformer_model_and_tokenizer,
    get_transformer_embeddings
)

from fewshot.utils import to_list, to_tensor


@attr.s
class Dataset(object):
    # These are the text (news articles, product descriptions, etc.)
    examples: List[str] = attr.ib()
    # Labels associated with each example
    # TODO: at some point this has to change because in a real application labels may
    #  not exist or there might be fewer labels than examples (need to keep track)
    labels: List[int] = attr.ib()
    # Categories that correspond to the number of unique Labels
    categories: List[str] = attr.ib()
    # embeddings for each example and each category
    _embeddings = attr.ib(default=None)

    def calc_sbert_embeddings(self):
        model, tokenizer = load_transformer_model_and_tokenizer()
        self._embeddings = get_transformer_embeddings(
            self.examples + self.categories, model, tokenizer
        )

    @property
    def embeddings(self):
        if not hasattr(self, "_embeddings") or self._embeddings is None:
            warnings.warn("Should run dataset.calc_sbert_embeddings() first.  In the future this will fail.")
            self.calc_sbert_embeddings()
            # raise Exception("Run dataset.calc_sbert_embeddings() first.")
        return self._embeddings


def expand_labels(dataset: Dataset):
    """ 
    When performing supervised learning (e.g. few-shot), we will need a label embedding for 
    each example in the dataset. Most datasets only have a handful of labels (4-10).
    Passing these repeatedly through SBERT for each example is slow, repetitive and
    unnecessarily expensive. 

    Instead we'll restructure the dataset attributes. Originally instantiated, each label 
    has already been passed through SBERT and is stored in dataset.embeddings 
    as the last N items in the list. These are used to build out a full label embedding tensor.
    Additionally, dataset.embeddings is repurposed to contain ONLY example embeddings 
    rather than example AND label embeddings
    """

    num_labels = len(dataset.categories)
    label_embeddings = to_list(dataset.embeddings[-num_labels:])

    dataset.label_embeddings = to_tensor([label_embeddings[label] for label in dataset.labels])
    #dataset.embeddings = dataset.embeddings[:-num_labels]
    return dataset


def select_subsample(df: pd.DataFrame, sample_size: int, random_state=42):
  """ Given a DataFrame, randomly subsample sample_size number of examples
      from each category
  """
  return (
      df
      .groupby('category', group_keys=False)
      .apply(lambda x: x.sample(min(len(x), sample_size), 
                                random_state=random_state))
      .assign(
          category = lambda df: pd.Categorical(df.category),
          label = lambda df: df.category.cat.codes
          )
      )