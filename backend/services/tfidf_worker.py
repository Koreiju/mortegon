import multiprocessing
from backend.services.global_tfidf_store import GlobalTfidfStore

def tfidf_worker_main(queue, store_dir):
    store = GlobalTfidfStore(store_dir)
    try:
        while True:
            batch = queue.get()
            if batch is None:
                break
            action = batch.get("action")
            if action == "add":
                store.add_chunks(batch["texts"], batch["metas"])
            elif action == "remove":
                store.remove_chunks(batch["chunk_ids"], match_prefix=False)
    finally:
        store.save()