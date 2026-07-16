from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from pydantic import BaseModel
from app.config import settings


class PipelineTriggerResponse(BaseModel):
    status: str
    message: str


def verify_pipeline_key(pipeline_key: str = Header(...)):
    if pipeline_key != settings.PIPELINE_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")


router = APIRouter(
    prefix="/pipeline", 
    tags=["pipeline"], 
    dependencies=[Depends(verify_pipeline_key)]
)


def run_ticker_sync_background():
    from app.database import get_db
    from app.pipeline.fetch_tickers import fetch_tickers
    from app.pipeline.clean_tickers import clean_tickers
    from app.pipeline.store_tickers import store_tickers

    db = next(get_db())
    try:
        raw_tickers = fetch_tickers()
        cleaned_tickers = clean_tickers(raw_tickers)
        store_tickers(cleaned_tickers, db)
        print(f"Ticker sync completed: {len(cleaned_tickers)} tickers processed successfully.")
    except Exception as e:
        print(f"Error during ticker sync: {e}")
        db.rollback()
    finally:
        db.close()


def run_ticker_status_background(min_posts, relevance_threshold):
    from app.database import get_db
    from app.pipeline.update_ticker_status import update_ticker_status

    db = next(get_db())
    try:
        args = {}
        if min_posts is not None:
            args['min_posts'] = min_posts
        if relevance_threshold is not None:
            args['relevance_threshold'] = relevance_threshold
        update_ticker_status(db, **args)
        print("Ticker status update completed successfully.")
    except Exception as e:
        print(f"Error during ticker status update: {e}")
        db.rollback()
    finally:
        db.close()


def run_scrape_pipeline_background(limit_tickers, limit_calls, all):
    from app.database import get_db
    from app.models.ticker import Ticker
    from app.pipeline.scrape_posts import scrape_posts
    from app.pipeline.store_posts import store_posts
    from app.pipeline.fetch_tickers import fetch_tickers
    from app.pipeline.clean_tickers import clean_tickers
    from app.pipeline.store_tickers import store_tickers

    db = next(get_db())
    try:
        tickers = fetch_tickers()
        cleaned_tickers = clean_tickers(tickers)
        store_tickers(cleaned_tickers, db)
        args = {}
        if limit_tickers is not None:
            args['limit_tickers'] = limit_tickers
        if limit_calls is not None:
            args['limit_calls'] = limit_calls
        if all:
            args['all'] = all
        posts = scrape_posts(cleaned_tickers, **args)
        store_posts(posts, db)
        print(f"Scraping completed: {len(posts)} posts stored.")
    except Exception as e:
        print(f"Error during scraping: {e}")
        db.rollback()
    finally:
        db.close()


def run_classification_pipeline_background(relevance_limit, sentiment_limit):
    from app.database import get_db
    from app.pipeline.llm_relevance import run_relevance_pipeline
    from app.pipeline.llm_sentiment import run_sentiment_pipeline

    db = next(get_db())
    try:
        relevance_args = {}
        sentiment_args = {}
        if relevance_limit is not None:
            relevance_args['limit'] = relevance_limit
        if sentiment_limit is not None:
            sentiment_args['limit'] = sentiment_limit
        run_relevance_pipeline(db, **relevance_args)
        run_sentiment_pipeline(db, **sentiment_args)
        print("Classification pipeline completed successfully.")
    except Exception as e:
        print(f"Error during classification: {e}")
        db.rollback()
    finally:
        db.close()


def run_verification_pipeline_background(user_id=None):
    from app.database import get_db
    from app.pipeline.verify_picks import run_verify_picks_pipeline, get_users_with_pending_posts

    db = next(get_db())
    try:
        if user_id:
            run_verify_picks_pipeline(user_id, db)
        else:
            users = get_users_with_pending_posts(db)
            for user in users:
                try:
                    run_verify_picks_pipeline(user[0], db)
                except Exception as e:
                    print(f"Error during verification for user {user[0]}: {e}")
                    db.rollback()
        print("Verification pipeline completed successfully.")
    except Exception as e:
        print(f"Error during verification: {e}")
        db.rollback()
    finally:
        db.close()


def run_ranking_pipeline_background(top_n=20):
    from app.database import get_db
    from app.pipeline.update_credibility import update_credibility_scores_for_users
    from app.pipeline.rank_picks import rank_picks
    from app.pipeline.store_top_picks import store_top_picks

    db = next(get_db())
    try:
        update_credibility_scores_for_users(db)
        ranked_posts = rank_picks(db)
        store_top_picks(db, ranked_posts, top_n=top_n)
        print("Ranking pipeline completed successfully.")
    except Exception as e:
        print(f"Error during ranking: {e}")
        db.rollback()
    finally:
        db.close()


@router.post("/tickers/sync", response_model=PipelineTriggerResponse)
def trigger_ticker_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_ticker_sync_background)
    return PipelineTriggerResponse(status="started", message="Ticker sync triggered in the background.")

@router.post("/tickers/status", response_model=PipelineTriggerResponse)
def trigger_ticker_status(background_tasks: BackgroundTasks, min_posts: int = None, relevance_threshold: float = None):
    background_tasks.add_task(run_ticker_status_background, min_posts=min_posts, relevance_threshold=relevance_threshold)
    return PipelineTriggerResponse(status="started", message="Ticker status update triggered in the background.")

@router.post("/scrape", response_model=PipelineTriggerResponse)
def trigger_scrape(background_tasks: BackgroundTasks, limit_tickers: int = None, limit_calls: int = None, all: bool = False):
    background_tasks.add_task(run_scrape_pipeline_background, limit_tickers=limit_tickers, limit_calls=limit_calls, all=all)
    return PipelineTriggerResponse(status="started", message="Scrape triggered in the background.")

@router.post("/classify", response_model=PipelineTriggerResponse)
def trigger_classification(background_tasks: BackgroundTasks, relevance_limit: int = None, sentiment_limit: int = None):
    background_tasks.add_task(run_classification_pipeline_background, relevance_limit=relevance_limit, sentiment_limit=sentiment_limit)
    return PipelineTriggerResponse(status="started", message="Classification pipeline triggered in the background.")

@router.post("/verify", response_model=PipelineTriggerResponse)
def trigger_verification(background_tasks: BackgroundTasks, user_id: str = None):
    background_tasks.add_task(run_verification_pipeline_background, user_id=user_id)
    return PipelineTriggerResponse(status="started", message="Verification pipeline triggered in the background.")

@router.post("/rank", response_model=PipelineTriggerResponse)
def trigger_ranking(background_tasks: BackgroundTasks, top_n: int = 20):
    background_tasks.add_task(run_ranking_pipeline_background, top_n=top_n)
    return PipelineTriggerResponse(status="started", message="Ranking pipeline triggered in the background.")
