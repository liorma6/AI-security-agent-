"""One predeclared augmentation continuation; validation alone selects the artifact."""

import math
import time

import torch

from phishguard.audit.runner import measures
from phishguard.baseline.common import read_bytes
from phishguard.baseline.metrics import select_threshold
from phishguard.baseline.model import text_hash
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.defense.common import PROTOCOL, DefenseError, identity
from phishguard.defense.data import verify_augmentation
from phishguard.defense.model import load_detector, parent, save_detector, snapshot
from phishguard.finetune.model import runtime, tensor_digest, token_report


def train(
    directory,
    reference,
    parent_directory,
    parent_selection,
    augmentation,
    augmentation_reference,
    review_reference,
    output,
    progress=None,
):
    if output.exists():
        raise DefenseError("output_already_exists")
    rows, _, views, manifest = verify_augmentation(
        directory, reference, augmentation, augmentation_reference, review_reference
    )
    detector = parent(parent_directory, parent_selection)
    before = snapshot(parent_directory)
    started = time.perf_counter()
    with runtime(PROTOCOL["seed"]):
        initial_encoder = tensor_digest(detector.network.bert.state_dict())
        initial_state = tensor_digest(detector.network.state_dict())
        encoded, counts = detector.encode([r.email for r in views["train"]])
        validation, valid_counts = detector.encode([r.email for r in views["validation"]])
        labels = [int(r.label == "phishing") for r in views["train"]]
        valid_labels = [int(r.label == "phishing") for r in views["validation"]]
        n_valid = len(rows["validation"])
        initial_scores, _ = detector.score_encoded(validation)
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
        total_steps = math.ceil(len(encoded) / PROTOCOL["batch_size"]) * PROTOCOL["epochs"]
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
                optimizer.zero_grad(set_to_none=True)
                loss = detector.network(
                    **detector.batch([encoded[i] for i in indices]),
                    labels=torch.tensor([labels[i] for i in indices]),
                ).loss
                if not torch.isfinite(loss).item():
                    raise DefenseError("nonfinite_defense_loss")
                loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(
                    detector.network.parameters(), PROTOCOL["max_gradient_norm"]
                )
                if not torch.isfinite(norm).item():
                    raise DefenseError("nonfinite_defense_gradient")
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
            scores, valid_loss = detector.score_encoded(validation, valid_labels)
            threshold, _ = select_threshold(valid_labels[:n_valid], scores[:n_valid])
            record = {
                "epoch": epoch,
                "training_mean_loss": summed_loss / len(encoded),
                "validation_mixed_mean_loss": valid_loss,
                "validation_clean": measures(rows["validation"], scores[:n_valid], threshold),
                "validation_perturbed": measures(rows["validation"], scores[n_valid:], threshold),
            }
            history.append(record)
            if valid_loss < best_loss:
                best_loss, selected_epoch = valid_loss, epoch
                best_state = {
                    k: v.detach().clone() for k, v in detector.network.state_dict().items()
                }
            if progress:
                progress({"status": "epoch_complete", **record})
        detector.network.load_state_dict(best_state, strict=True)
        scores, selected_loss = detector.score_encoded(validation, valid_labels)
        threshold, candidates = select_threshold(valid_labels[:n_valid], scores[:n_valid])
        final_encoder = tensor_digest(detector.network.bert.state_dict())
        if initial_encoder == final_encoder:
            raise DefenseError("defense_encoder_not_updated")
        saved, selection = save_detector(
            detector,
            parent_directory,
            output,
            threshold,
            selected_epoch,
            [text_hash(r.email) for r in views["train"] + views["validation"]],
            digest(read_bytes(augmentation_reference)),
            digest(read_bytes(review_reference)),
        )
        restored, _ = load_detector(output).score_encoded(validation)
        error = max(abs(a - b) for a, b in zip(scores, restored, strict=True))
        if error > 1e-7:
            raise DefenseError("defense_reload_score_mismatch")
        train_scores, _ = detector.score_encoded(encoded)
    if snapshot(parent_directory) != before:
        raise DefenseError("defense_parent_files_changed")
    report = {
        **identity(),
        "phase": "train-only-augmentation-validation-selection",
        "selection": selection,
        "dataset_sha256": manifest["dataset_sha256"],
        "augmentation_partitions": manifest["partitions"],
        "fit_rows": len(encoded),
        "fit_original_parents": len(rows["train"]),
        "validation_parents": n_valid,
        "test_challenge_or_reserve_files_opened": False,
        "parent_files_before": before,
        "parent_files_unchanged": True,
        "initial_state_sha256": initial_state,
        "initial_encoder_sha256": initial_encoder,
        "final_encoder_sha256": final_encoder,
        "encoder_updated": True,
        "epochs": history,
        "selected_epoch": selected_epoch,
        "selected_validation_mixed_loss": selected_loss,
        "threshold_candidates": candidates,
        "training_metrics": measures(views["train"], train_scores, threshold),
        "validation_clean": measures(rows["validation"], scores[:n_valid], threshold),
        "validation_perturbed": measures(rows["validation"], scores[n_valid:], threshold),
        "parent_validation_clean": measures(
            rows["validation"], initial_scores[:n_valid], PROTOCOL["parent_threshold"]
        ),
        "parent_validation_perturbed": measures(
            rows["validation"], initial_scores[n_valid:], PROTOCOL["parent_threshold"]
        ),
        "validation_clean_at_parent_threshold": measures(
            rows["validation"], scores[:n_valid], PROTOCOL["parent_threshold"]
        ),
        "validation_clean_at_default_threshold": measures(
            rows["validation"], scores[:n_valid], 0.5
        ),
        "tokens": {
            "training_views": token_report(counts),
            "validation_views": token_report(valid_counts),
        },
        "reload_max_absolute_score_error": error,
        "model_revision": saved["model_revision"],
        "elapsed_seconds": time.perf_counter() - started,
        "limitation": PROTOCOL["limitations"],
    }
    (output / "training-report.json").write_bytes(json_bytes(report))
    return report
