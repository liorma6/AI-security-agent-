"""One fixed fine-tuning run; validation chooses an epoch and then a threshold."""

import math
import time

import torch

from phishguard.audit.runner import measures
from phishguard.baseline.common import code_revision, environment
from phishguard.baseline.metrics import select_threshold
from phishguard.baseline.model import check_training_boundary, text_hash
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.finetune.common import (
    PROTOCOL,
    PROTOCOL_SHA256,
    SOURCE,
    SOURCE_SHA256,
    STUDY,
    STUDY_SHA256,
    FineTuneError,
    partition,
    study,
)
from phishguard.finetune.model import (
    initialize,
    load_detector,
    runtime,
    save_detector,
    tensor_digest,
    token_report,
)


def run_identity():
    from importlib.metadata import version

    return {
        "report_version": "1.0",
        "protocol": PROTOCOL,
        "protocol_sha256": PROTOCOL_SHA256,
        "source": SOURCE,
        "source_sha256": SOURCE_SHA256,
        "study": STUDY,
        "study_sha256": STUDY_SHA256,
        "environment": {
            **environment(),
            "neural_packages": {p: version(p) for p in PROTOCOL["runtime"]},
            "neural_device": "cpu",
            "neural_threads": PROTOCOL["numeric_threads"],
        },
        "code": code_revision(),
        "reserve_rows_scored": 0,
    }


def train(directory, reference, source_directory, output, progress=None):
    if output.exists():
        raise FineTuneError("output_already_exists")
    frozen = study(directory, reference)
    training, validation = partition(frozen, "train"), partition(frozen, "validation")
    check_training_boundary(training, validation)
    started = time.perf_counter()
    with runtime(PROTOCOL["seed"]):
        detector = initialize(source_directory)
        encoded, train_counts = detector.encode([r.email for r in training])
        valid_encoded, valid_counts = detector.encode([r.email for r in validation])
        labels = [int(r.label == "phishing") for r in training]
        valid_labels = [int(r.label == "phishing") for r in validation]
        initial_encoder = tensor_digest(detector.network.bert.state_dict())
        decay, no_decay = [], []
        for name, parameter in detector.network.named_parameters():
            (no_decay if name.endswith("bias") or "LayerNorm.weight" in name else decay).append(
                parameter
            )
        optimizer = torch.optim.AdamW(
            [
                {"params": decay, "weight_decay": PROTOCOL["weight_decay"]},
                {"params": no_decay, "weight_decay": 0.0},
            ],
            lr=PROTOCOL["learning_rate"],
            betas=tuple(PROTOCOL["adam_betas"]),
            eps=PROTOCOL["adam_epsilon"],
        )
        steps_per_epoch = math.ceil(len(encoded) / PROTOCOL["batch_size"])
        total_steps = steps_per_epoch * PROTOCOL["epochs"]
        warmup = math.ceil(total_steps * PROTOCOL["warmup_fraction"])

        def factor(step):
            return (
                step / max(1, warmup)
                if step < warmup
                else max(0.0, (total_steps - step) / max(1, total_steps - warmup))
            )

        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, factor)
        history, best_loss, best_state, selected_epoch = [], math.inf, None, None
        shuffle = torch.Generator().manual_seed(PROTOCOL["seed"])
        for epoch in range(1, PROTOCOL["epochs"] + 1):
            detector.network.train()
            order = torch.randperm(len(encoded), generator=shuffle).tolist()
            summed_loss = 0.0
            for start in range(0, len(order), PROTOCOL["batch_size"]):
                indices = order[start : start + PROTOCOL["batch_size"]]
                batch = detector.batch([encoded[i] for i in indices])
                optimizer.zero_grad(set_to_none=True)
                loss = detector.network(
                    **batch, labels=torch.tensor([labels[i] for i in indices])
                ).loss
                if not torch.isfinite(loss).item():
                    raise FineTuneError("nonfinite_training_loss")
                loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(
                    detector.network.parameters(), PROTOCOL["max_gradient_norm"]
                )
                if not torch.isfinite(norm).item():
                    raise FineTuneError("nonfinite_training_gradient")
                optimizer.step()
                scheduler.step()
                summed_loss += loss.item() * len(indices)
                if progress:
                    progress(
                        {
                            "status": "training",
                            "epoch": epoch,
                            "epochs": PROTOCOL["epochs"],
                            "rows": min(start + len(indices), len(order)),
                            "total": len(order),
                        }
                    )
            scores, valid_loss = detector.score_encoded(valid_encoded, valid_labels)
            threshold, _ = select_threshold(valid_labels, scores)
            history.append(
                {
                    "epoch": epoch,
                    "training_mean_loss": summed_loss / len(encoded),
                    "validation_mean_loss": valid_loss,
                    "validation_metrics": measures(validation, scores, threshold),
                }
            )
            if valid_loss < best_loss:
                best_loss, selected_epoch = valid_loss, epoch
                best_state = {
                    k: v.detach().clone() for k, v in detector.network.state_dict().items()
                }
            if progress:
                progress({"status": "epoch_complete", **history[-1]})
        detector.network.load_state_dict(best_state, strict=True)
        scores, selected_loss = detector.score_encoded(valid_encoded, valid_labels)
        threshold, candidates = select_threshold(valid_labels, scores)
        final_encoder = tensor_digest(detector.network.bert.state_dict())
        if initial_encoder == final_encoder:
            raise FineTuneError("encoder_weights_not_updated")
        manifest, selection = save_detector(
            detector,
            source_directory,
            output,
            threshold,
            selected_epoch,
            [text_hash(r.email) for r in training + validation],
        )
        reloaded = load_detector(output)
        restored, _ = reloaded.score_encoded(valid_encoded)
        error = max(abs(a - b) for a, b in zip(scores, restored, strict=True))
        if error > 1e-7:
            raise FineTuneError("finetuned_reload_score_mismatch")
        train_scores, _ = detector.score_encoded(encoded)
    report = {
        **run_identity(),
        "phase": "finetuning-train-validation",
        "selection": selection,
        "dataset_manifest_sha256": frozen.sha256,
        "fit_rows": len(training),
        "validation_rows": len(validation),
        "test_rows_used": 0,
        "challenge_rows_used": 0,
        "reserve_file_opened": False,
        "fit_ids_sha256": digest(json_bytes(sorted(r.example_id for r in training))),
        "validation_ids_sha256": digest(json_bytes(sorted(r.example_id for r in validation))),
        "selected_epoch": selected_epoch,
        "selected_validation_loss": selected_loss,
        "epochs": history,
        "threshold_candidates": candidates,
        "training_metrics": measures(training, train_scores, threshold),
        "validation_metrics": measures(validation, scores, threshold),
        "validation_at_default_threshold": measures(validation, scores, 0.5),
        "tokens": {"train": token_report(train_counts), "validation": token_report(valid_counts)},
        "parameter_count": sum(p.numel() for p in detector.network.parameters()),
        "encoder_before_sha256": initial_encoder,
        "encoder_after_sha256": final_encoder,
        "encoder_updated": True,
        "reload_max_absolute_score_error": error,
        "model_revision": manifest["model_revision"],
        "elapsed_seconds": time.perf_counter() - started,
        "single_seed_limit": "One fixed configuration/seed. "
        "Identical-seed reproduction tests execution, "
        "not variability across seeds.",
    }
    (output / "training-report.json").write_bytes(json_bytes(report))
    return report
