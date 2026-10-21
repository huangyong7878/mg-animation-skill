"""R5 provider registry: capability declarations separate from R0 and adapters.

Only registered, implemented providers are invokable. Metadata for future providers
does not imply implementation, image/video/audio abilities, or QA approval.
"""
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class Provider:
    name: str
    review: Callable
    modalities: frozenset
    scope: str
    can_verify_full_motion: bool = False
    can_verify_audio: bool = False

def providers():
    # Lazy import avoids injecting vendor code into R0's core state machine.
    from workflow.r5_provider import review_deepseek
    return {
        "deepseek": Provider(
            name="deepseek", review=review_deepseek,
            modalities=frozenset({"sampled_images"}),
            scope="sampled_frames_only",
            can_verify_full_motion=False, can_verify_audio=False,
        ),
    }

def provider_names():
    return tuple(sorted(providers()))

def select_provider(name):
    registered = providers()
    if name not in registered:
        raise ValueError(
            "Unsupported R5 provider: " + str(name) +
            "; implemented providers: " + ", ".join(sorted(registered)))
    return registered[name]

def run_review(provider_name, workdir, artifact_root, *, model=None, **provider_options):
    adapter = select_provider(provider_name)
    options = {"model": model} if model is not None else {}
    options.update(provider_options)
    result = adapter.review(workdir, artifact_root, **options)
    if not isinstance(result, dict):
        raise ValueError("R5 provider did not return an audit result")
    # An image-only provider may not escalate a model observation into R5 pass.
    if not adapter.can_verify_full_motion or not adapter.can_verify_audio:
        if result.get("status") != "pending":
            raise ValueError("Incomplete R5 modality coverage must remain pending")
    return result
