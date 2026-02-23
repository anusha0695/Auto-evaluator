#!/usr/bin/env python3
"""Main script to test end-to-end classification"""

import argparse
import json
import os
from pathlib import Path
from src.document_processor import DocumentProcessor
from src.primary_classifier_agent import PrimaryClassifierAgent
from src.config import settings


def main():
    parser = argparse.ArgumentParser(
        description="Classify clinical PDF document",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Default configuration (from .env):
  Input PDF:  {settings.default_input_pdf}
  Output Dir: {settings.default_output_dir}
  Output File: {settings.default_output_file}
  
Examples:
  # Use defaults from config
  python run_classification.py
  
  # Specify PDF only
  python run_classification.py data/input/raw_documents/doc2_13.pdf
  
  # Specify both PDF and output
  python run_classification.py doc2_25.pdf --output results/doc2_25.json
        """
    )
    parser.add_argument(
        "pdf_path", 
        nargs='?',  # Makes it optional
        help=f"Path to PDF file (default: {settings.default_input_pdf})"
    )
    parser.add_argument(
        "--output", "-o", 
        help=f"Output JSON file path (default: {settings.default_output_dir}/{settings.default_output_file})", 
        default=None
    )
    
    args = parser.parse_args()
    
    # Use defaults from config if not provided
    pdf_path = args.pdf_path if args.pdf_path else settings.default_input_pdf
    
    # Resolve relative paths to absolute
    pdf_path = Path(pdf_path)
    if not pdf_path.is_absolute():
        pdf_path = Path.cwd() / pdf_path
    
    # Check if PDF exists
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        return 1
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path
    else:
        # Use default output directory
        output_dir = Path(settings.default_output_dir)
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / settings.default_output_file
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize components
    print("Initializing Document Processor...")
    doc_processor = DocumentProcessor()
    
    print("Initializing Primary Classifier...")
    classifier = PrimaryClassifierAgent()
    
    # Process document or load existing bundle
    print(f"\nProcessing PDF: {pdf_path}")
    bundle_dir = Path("output/document_bundles")
    bundle_path = bundle_dir / f"bundle_{pdf_path.stem}.json"
    
    if bundle_path.exists():
        print(f"Loading existing bundle: {bundle_path}")
        from src.schemas import DocumentBundle
        with open(bundle_path, 'r', encoding='utf-8') as f:
            bundle_data = json.load(f)
        doc_bundle = DocumentBundle.model_validate(bundle_data)
        print(f"Loaded bundle with {doc_bundle.total_pages} pages")
    else:
        doc_bundle = doc_processor.process_pdf(str(pdf_path))
        print(f"Extracted {doc_bundle.total_pages} pages")
    
    # Format for LLM
    document_text = doc_processor.format_for_llm(doc_bundle)
    
    # Classify
    print("\nClassifying document...")
    classification = classifier.classify(document_text)
    
    # Assign document type to bundle from classification result
    doc_bundle.document_type = classification.dominant_type_overall.value
    print(f"Document type assigned: {doc_bundle.document_type}")
    
    # Run verification with AUTO_RETRY support
    print("\nRunning verification agents (V1-V5) with auto-retry...")
    from src.agents import RetryOrchestrator
    
    orchestrator = RetryOrchestrator()
    final_classification, verification_report, arbiter_decision, retry_log = orchestrator.verify_with_retry(
        classification, doc_bundle
    )
    
    # Update report with retry info
    if retry_log:
        verification_report.retry_attempts = len(retry_log)
        all_fixes = []
        for entry in retry_log:
            all_fixes.extend(entry['fixes_applied'])
        verification_report.fixes_applied = all_fixes
    
    # Display classification results
    print("\n" + "="*60)
    print("CLASSIFICATION RESULTS")
    print("="*60)
    print(f"Document: {pdf_path.name}")
    print(f"Dominant Type: {final_classification.dominant_type_overall.value}")
    print(f"Number of Segments: {final_classification.number_of_segments}")
    print(f"\nVendor Signals: {', '.join(final_classification.vendor_signals) if final_classification.vendor_signals else 'None'}")
    
    print("\nDocument Mixture:")
    for mix in final_classification.document_mixture:
        if mix.presence_level.value != "NO_EVIDENCE":
            print(f"  - {mix.document_type.value}: {mix.presence_level.value} ({mix.overall_share:.1%} share, {mix.confidence:.2f} confidence)")
    
    # Display verification report
    from src.agents import VerificationRunner
    verifier = VerificationRunner()  # For display method only
    verifier.print_report_summary(verification_report)
    
    # Display retry log if retries occurred
    if retry_log:
        print("\n" + "="*60)
        print("AUTO-RETRY LOG")
        print("="*60)
        print(f"Total Retry Attempts: {len(retry_log)}")
        for entry in retry_log:
            print(f"\n  Attempt {entry['attempt']}:")
            print(f"    Issues before fix: {entry['issues_before_fix']}")
            print(f"    Fixable issues: {entry['fixable_issues']}")
            print(f"    Fixes applied: {len(entry['fixes_applied'])}")
            for fix in entry['fixes_applied']:
                print(f"      - {fix}")
    
    # Display arbiter decision
    print("\n" + "="*60)
    print("ARBITER FINAL DECISION")
    print("="*60)
    print(f"Decision: {arbiter_decision.decision}")
    print(f"Reason:   {arbiter_decision.reason}")
    print(f"\nIssues Analyzed: {arbiter_decision.issues_analyzed}")
    print(f"  BLOCKER: {arbiter_decision.blocker_count}")
    print(f"  MAJOR:   {arbiter_decision.major_count}")
    print(f"  MINOR:   {arbiter_decision.minor_count}")
    print(f"  Fixable: {arbiter_decision.fixable_count}")
    
    # Save final classification to file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_classification.model_dump(), f, indent=2)
    print(f"\n✓ Final classification output saved to: {output_path}")
    
    # Save DocumentBundle for future use (SME review, evidence verification, etc.)
    bundle_dir = Path("output/document_bundles")
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = bundle_dir / f"bundle_{pdf_path.stem}.json"
    with open(bundle_path, 'w', encoding='utf-8') as f:
        json.dump(doc_bundle.model_dump(mode='json'), f, indent=2, default=str)
    print(f"✓ DocumentBundle saved to: {bundle_path}")
    
    # Save verification report with arbiter decision and retry log
    verification_output_path = output_path.parent / f"{output_path.stem}_verification.json"
    verification_data = verification_report.model_dump()
    verification_data['arbiter_decision'] = arbiter_decision.model_dump()
    verification_data['retry_log'] = retry_log
    with open(verification_output_path, 'w', encoding='utf-8') as f:
        json.dump(verification_data, f, indent=2)
    print(f"✓ Verification report saved to: {verification_output_path}")
    
    # Auto-generate SME packet if escalated
    if arbiter_decision.decision == "ESCALATE_TO_SME":
        print(f"\n{'='*60}")
        print("GENERATING SME REVIEW PACKET")
        print(f"{'='*60}")
        
        from src.evaluation.packet_generator import SMEPacketGenerator
        
        generator = SMEPacketGenerator()
        
        # Use relative path for bundle (make relative only if absolute)
        bundle_path_str = str(bundle_path.relative_to(Path.cwd())) if bundle_path.is_absolute() else str(bundle_path)
        
        sme_packet = generator.generate_packet(
            pdf_path=str(pdf_path),
            primary_classification=final_classification,
            verification_report=verification_report,
            arbiter_decision=arbiter_decision,
            document_bundle_path=bundle_path_str
        )
        
        # Save SME packet
        packet_path = generator.save_packet(sme_packet)
        print(f"\n✓ SME review packet generated: {packet_path}")
        print(f"  Total issues for SME review: {sme_packet.total_issues}")
        print(f"  Notebook: notebooks/sme_review_interface.ipynb")
    
    return 0


if __name__ == "__main__":
    exit(main())
