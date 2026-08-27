import numpy as np
import pandas as pd
from scipy.optimize import minimize


class MLE:
    """Estimate the AI mixture share from token-presence probabilities."""

    def __init__(self, word_df_path):
        word_df = pd.read_parquet(word_df_path)
        required = {"Word", "logP", "logQ", "log1-P", "log1-Q"}
        missing = required.difference(word_df.columns)
        if missing:
            raise ValueError(f"Vocabulary parquet is missing columns: {sorted(missing)}")

        self.all_tokens_set = set(word_df["Word"])
        self.log_p_hat = dict(zip(word_df["Word"], word_df["logP"]))
        self.log_q_hat = dict(zip(word_df["Word"], word_df["logQ"]))
        self.log_one_minus_p_hat = dict(zip(word_df["Word"], word_df["log1-P"]))
        self.log_one_minus_q_hat = dict(zip(word_df["Word"], word_df["log1-Q"]))

    @staticmethod
    def _negative_log_likelihood(alpha_array, log_p_values, log_q_values):
        alpha = float(alpha_array[0])
        with np.errstate(divide="ignore"):
            mixture = np.logaddexp(
                np.log1p(-alpha) + log_p_values,
                np.log(alpha) + log_q_values,
            )
        return -float(np.mean(mixture))

    def precompute_log_probabilities(self, data):
        """Precompute sentence-level log probabilities under the two vocabularies."""
        total_log_one_minus_p = sum(self.log_one_minus_p_hat.values())
        total_log_one_minus_q = sum(self.log_one_minus_q_hat.values())
        log_p_values = data.apply(
            lambda tokens: sum(self.log_p_hat[token] for token in tokens)
            + total_log_one_minus_p
            - sum(self.log_one_minus_p_hat[token] for token in tokens)
        )
        log_q_values = data.apply(
            lambda tokens: sum(self.log_q_hat[token] for token in tokens)
            + total_log_one_minus_q
            - sum(self.log_one_minus_q_hat[token] for token in tokens)
        )
        return log_p_values.to_numpy(dtype=float), log_q_values.to_numpy(dtype=float)

    def estimate_alpha(self, data):
        """Estimate the AI mixture share for a collection of token sets."""
        if len(data) == 0:
            raise ValueError("No valid sentences are available for MLE estimation.")

        log_p_values, log_q_values = self.precompute_log_probabilities(data)
        result = minimize(
            self._negative_log_likelihood,
            x0=[0.5],
            args=(log_p_values, log_q_values),
            method="L-BFGS-B",
            bounds=[(0.0, 1.0)],
        )
        if not result.success:
            raise RuntimeError(f"MLE optimization failed: {result.message}")

        alpha = float(result.x[0])
        if not np.isfinite(alpha) or not 0.0 <= alpha <= 1.0:
            raise RuntimeError(f"MLE optimization returned an invalid alpha: {alpha}")
        return round(alpha, 6)

    def estimate_from_dataframe(self, inference_data, exploded_data=False):
        """Estimate alpha from a DataFrame containing an inference_sentence column."""
        if "inference_sentence" not in inference_data.columns:
            raise ValueError("Inference data is missing the inference_sentence column.")
        if not exploded_data:
            inference_data = inference_data.explode("inference_sentence")
        inference_data = inference_data.dropna(subset=["inference_sentence"])
        inference_data = inference_data[
            inference_data["inference_sentence"].map(lambda sentence: len(sentence) > 1)
        ]
        data = inference_data["inference_sentence"].map(
            lambda sentence: set(sentence).intersection(self.all_tokens_set)
        )
        data = data.reset_index(drop=True)
        return self.estimate_alpha(data)

    def inference(self, inference_file_path, exploded_data=False):
        """Estimate alpha from a parquet file for backward compatibility."""
        inference_data = pd.read_parquet(inference_file_path)
        return self.estimate_from_dataframe(inference_data, exploded_data=exploded_data)
