from inversebias.ml import (
    build_inverse_bias,
    filter_subjects_of_interest,
    infer_sentiment,
)
from inversebias.scrape import build_today


def today_pipeline(upload=True, verbose=False):
    title = build_today(upload=upload, verbose=verbose)
    subject = filter_subjects_of_interest(title, upload=upload, verbose=verbose)
    sentiment = infer_sentiment(subject, upload=upload, online=True, verbose=verbose)
    bias = build_inverse_bias(sentiment, upload=upload)
    return bias


if __name__ == "__main__":
    upload = True
    verbose = True
    today_pipeline(upload=upload, verbose=verbose)
