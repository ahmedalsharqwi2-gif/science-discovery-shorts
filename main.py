# -*- coding: utf-8 -*-
"""
main.py - نقطة الدخول الرئيسية
=================================
متحكم المشروع - ينسق بين جميع وحدات المشروع.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

# Setup logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("pipeline")

from scripts import (
    ContentGenerator,
    VoiceGenerator,
    QualityCheckPipeline,
    ContentPublisher,
)
from scripts.assemble_video import assemble_video, probe_duration
from scripts.audio_duration import fit_narration, target_words_for_duration
from scripts.publish_content import build_social_description
from scripts.broll_quality_pipeline import evaluate as evaluate_broll
from scripts.topic_history import TopicHistory

MIN_AUDIO_SECONDS = float(os.getenv("MIN_AUDIO_SECONDS", "90"))
MAX_AUDIO_SECONDS = float(os.getenv("MAX_AUDIO_SECONDS", "180"))


class AutoPublishPipeline:
    """خط الأنابيب الرئيسي لتوليد ونشر المحتوى."""

    def __init__(self):
        self.content_generator = ContentGenerator(
            min_words=int(os.getenv("MIN_WORDS", "180")),
            max_words=int(os.getenv("MAX_WORDS", "400")),
        )
        self.voice_generator = VoiceGenerator(
            output_dir=Path(os.getenv("OUTPUT_DIR", "./output"))
        )
        self.quality_checker = QualityCheckPipeline(
            min_acceptable_score=float(os.getenv("MIN_QUALITY_SCORE", "0.75"))
        )
        self.publisher = ContentPublisher()
        self.topic_history_path = Path(os.getenv("TOPIC_HISTORY_FILE", "topic_history.json"))

    def run(self, category: str = "", topic: Optional[str] = None) -> bool:
        """Run the complete pipeline."""
        log.info("\n" + "="*60)
        log.info("Starting Auto-Publish Pipeline")
        log.info("="*60)

        try:
            # Step 1: Generate topic
            if topic is None:
                log.info("\n[Step 1] Generating topic...")
                topic = self.content_generator.generate_topic(category)
                log.info(f"✓ Topic generated: {topic[:80]}...")
            else:
                log.info(f"\n[Step 1] Using provided topic: {topic[:80]}...")

            # Check the durable per-repository history even for an explicitly
            # supplied topic; the generator also applies this gate itself.
            TopicHistory(self.topic_history_path).check_unique({"title": topic})

            # Step 2: Generate narration
            log.info("\n[Step 2] Generating narration...")
            narration = self.content_generator.generate_narration(topic)
            log.info(f"✓ Narration generated ({len(narration.split())} words)")

            # Step 3: Quality check
            log.info("\n[Step 3] Checking content quality...")
            checked_text, text_report = self.quality_checker.check_text(narration)
            log.info(f"✓ Quality check complete (score: {text_report.overall_score:.2f}/1.0)")

            if not text_report.is_acceptable:
                log.error("Content quality not acceptable for publishing")
                return False

            # Fact checking is disabled for the current publishing workflow.
            # Keep the gate available behind an explicit opt-in for controlled
            # runs, while never exposing source URLs in public descriptions.
            source_urls = []
            if os.getenv("FACT_CHECK_ENABLED", "false").lower() == "true":
                from fact_check import fact_check_topic
                log.info("\n[Step 3.5] Fact-checking scientific claims...")
                fact_report = fact_check_topic(
                    {
                        "title": topic,
                        "narration_script": checked_text,
                    },
                    output_path=Path("state/fact_check.json"),
                )
                if fact_report.get("status") != "PASS":
                    log.error("Scientific fact-check rejected the episode: %s", fact_report.get("errors"))
                    return False
                log.info("✓ Scientific fact-check passed with %d source(s)", len(fact_report.get("source_urls", [])))
            else:
                log.info("✓ Scientific fact-check disabled by FACT_CHECK_ENABLED")

            # Step 4: Generate voice
            log.info("\n[Step 4] Generating voice...")
            output_path, success = self.voice_generator.generate(
                checked_text,
                output_path=Path("output/narration.mp3"),
            )

            if not success:
                log.error("Voice generation failed")
                return False

            log.info(f"✓ Voice generated: {output_path}")

            # Step 5: Fit narration naturally. If the required tempo change
            # would exceed the safe limit, shorten the script and regenerate TTS.
            log.info("\n[Step 5] Fitting narration to the reel duration...")
            max_shorten_attempts = max(0, int(os.getenv("MAX_NARRATION_SHORTEN_ATTEMPTS", "2")))
            minimum_short_script_words = max(20, int(os.getenv("MIN_SHORTENED_NARRATION_WORDS", "45")))
            fitted = False
            for shorten_attempt in range(max_shorten_attempts + 1):
                actual_duration = probe_duration(Path(output_path))
                tempo_needed = actual_duration / max(1.0, MAX_AUDIO_SECONDS - 0.25)
                if actual_duration > MAX_AUDIO_SECONDS and tempo_needed > 1.25:
                    if shorten_attempt >= max_shorten_attempts:
                        raise ValueError(
                            f"Narration remains too long after {max_shorten_attempts} shortening attempts: "
                            f"{actual_duration:.2f}s (safe max {MAX_AUDIO_SECONDS:.2f}s)"
                        )
                    target_words = target_words_for_duration(
                        len(checked_text.split()), actual_duration, MAX_AUDIO_SECONDS,
                        minimum_words=minimum_short_script_words,
                    )
                    log.warning(
                        "Narration is %.2fs; shortening from %d words toward %d before regenerating TTS (%d/%d)",
                        actual_duration, len(checked_text.split()), target_words,
                        shorten_attempt + 1, max_shorten_attempts,
                    )
                    checked_text = self.content_generator.shorten_narration(topic, checked_text, target_words)
                    checked_text, text_report = self.quality_checker.check_text(checked_text)
                    log.info("Shortened narration quality score: %.2f/1.0", text_report.overall_score)
                    if not text_report.is_acceptable:
                        log.error("Shortened narration failed the text quality gate")
                        return False
                    if os.getenv("FACT_CHECK_ENABLED", "false").lower() == "true":
                        from fact_check import fact_check_topic
                        fact_report = fact_check_topic(
                            {"title": topic, "narration_script": checked_text},
                            output_path=Path("state/fact_check.json"),
                        )
                        if fact_report.get("status") != "PASS":
                            log.error("Shortened narration failed scientific fact-check: %s", fact_report.get("errors"))
                            return False
                    output_path, success = self.voice_generator.generate(
                        checked_text, output_path=Path("output/narration.mp3")
                    )
                    if not success:
                        log.error("Voice regeneration failed after narration shortening")
                        return False
                    continue

                fit_narration(
                    Path(output_path), MIN_AUDIO_SECONDS, MAX_AUDIO_SECONDS,
                    float(os.getenv("TARGET_AUDIO_SECONDS", "135")),
                )
                fitted = True
                break

            if not fitted:
                raise ValueError("Narration could not be fitted inside the video duration window")

            log.info("\n[Step 5.5] Checking audio quality...")
            audio_report = self.quality_checker.check_audio(output_path, checked_text)
            log.info(f"✓ Audio quality check complete (score: {audio_report.overall_score:.2f}/1.0)")

            if not audio_report.is_acceptable:
                log.error("Audio quality not acceptable for publishing")
                return False

            audio_duration = probe_duration(output_path)
            log.info("✓ Audio duration: %.2fs (required %.0f–%.0fs; reels safety cap)", audio_duration, MIN_AUDIO_SECONDS, MAX_AUDIO_SECONDS)
            if not MIN_AUDIO_SECONDS <= audio_duration <= MAX_AUDIO_SECONDS:
                log.error(
                    "Audio duration outside publishing window: %.2fs; refusing to publish",
                    audio_duration,
                )
                return False

            # Build the actual vertical MP4 before publishing. Previously the
            # pipeline sent narration.mp3 to Buffer, so there was no visual
            # layer or on-screen Arabic text at all.
            log.info("\n[Step 6] Assembling vertical video with Arabic captions...")
            video_path = assemble_video(
                output_path,
                checked_text,
                Path("output/final_video.mp4"),
                topic=topic,
            )
            log.info(f"✓ Video assembled: {video_path}")

            # Validate the rendered B-roll track before any external publish.
            broll_report = evaluate_broll(
                video_path,
                manifest=Path("state/cinematic_scene_manifest.json") if os.getenv("CINEMATIC_ENABLED", "false").lower() == "true" else None,
                clips_dir=Path("output/pexels_clips"),
                report_path=Path("state/montage_quality.json"),
                expected="vertical",
                min_clips=4,
                max_black_seconds=0.30,
            )
            if not broll_report["passed"]:
                log.warning("B-roll/montage quality warnings: %s", broll_report["errors"])
                if os.getenv("QUALITY_GATES_BLOCKING", "true").lower() == "true":
                    return False
            else:
                log.info("✓ B-roll/montage quality gate passed (%d source clips)", broll_report["broll"]["clip_count"])

            # Step 7: Publish
            log.info("\n[Step 7] Publishing content...")
            title = topic[:60]
            description = build_social_description(topic, narration, source_urls=source_urls)
            channels = os.getenv("PUBLISH_CHANNELS", "youtube,tiktok,instagram").split(",")

            if os.getenv("PUBLISH_DRY_RUN", "false").lower() == "true":
                log.info("DRY RUN: skipping external publication")
                log.info("DRY RUN metadata: %s", description[:500])
                return True

            # Persist the reservation to the repository before contacting any
            # external publisher. If the GitHub write fails, fail closed.
            topic_candidate = {
                "title": topic,
                "hook": " ".join(checked_text.split()[:35]),
            }
            topic_history = TopicHistory(self.topic_history_path)
            topic_history.reserve(topic_candidate, source="science-pipeline", commit=True)

            publish_success = self.publisher.publish_to_buffer(
                video_path=video_path,
                title=title,
                description=description,
                channel_ids=channels,
            )

            if not publish_success:
                log.error("Publishing was not confirmed for every compatible configured channel")
                return False
            topic_history.mark_published(topic_candidate, commit=True)
            log.info("✓ Content published successfully to all compatible configured channels; incompatible channels are logged as skipped")

            log.info("\n" + "="*60)
            log.info("Pipeline completed successfully!")
            log.info("="*60 + "\n")
            return True

        except Exception as e:
            log.error(f"Pipeline failed: {e}", exc_info=True)
            return False


if __name__ == "__main__":
    pipeline = AutoPublishPipeline()
    
    # Get topic from environment or command line
    topic = os.getenv("TOPIC") or (sys.argv[1] if len(sys.argv) > 1 else None)
    category = os.getenv("CATEGORY", "عام")
    
    success = pipeline.run(category=category, topic=topic)
    sys.exit(0 if success else 1)
