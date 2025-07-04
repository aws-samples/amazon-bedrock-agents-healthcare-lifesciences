#!/usr/bin/env python3
"""
Data Validation Script for Harmonized Pipeline Data

This script validates the harmonized pharmaceutical pipeline data
to ensure data quality and schema compliance.

Author: Data Science Team
Date: 2025-07-03
"""

import json
from pathlib import Path
from collections import Counter, defaultdict
import re

class PipelineDataValidator:
    """Class to validate harmonized pharmaceutical pipeline data"""
    
    def __init__(self, data_file):
        self.data_file = Path(data_file)
        self.data = None
        self.validation_results = {
            "overall_status": "UNKNOWN",
            "total_candidates": 0,
            "validation_checks": {},
            "errors": [],
            "warnings": [],
            "summary": {}
        }
        
    def load_data(self):
        """Load harmonized data from JSON file"""
        try:
            with open(self.data_file, 'r') as f:
                self.data = json.load(f)
            print(f"✓ Loaded data from {self.data_file}")
            return True
        except FileNotFoundError:
            print(f"✗ Could not find {self.data_file}")
            return False
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON format: {e}")
            return False
    
    def validate_schema_structure(self):
        """Validate the overall schema structure"""
        required_root_keys = [
            "metadata", "companies", "unified_pipeline", 
            "therapeutic_areas", "development_phases", 
            "compound_types", "summary_statistics"
        ]
        
        errors = []
        for key in required_root_keys:
            if key not in self.data:
                errors.append(f"Missing required root key: {key}")
        
        self.validation_results["validation_checks"]["schema_structure"] = {
            "status": "PASS" if not errors else "FAIL",
            "errors": errors
        }
        
        if errors:
            self.validation_results["errors"].extend(errors)
    
    def validate_metadata(self):
        """Validate metadata section"""
        metadata = self.data.get("metadata", {})
        required_fields = [
            "harmonization_date", "version", "description", 
            "data_sources", "total_companies", "total_candidates"
        ]
        
        errors = []
        warnings = []
        
        for field in required_fields:
            if field not in metadata:
                errors.append(f"Missing metadata field: {field}")
        
        # Validate data sources
        if "data_sources" in metadata:
            data_sources = metadata["data_sources"]
            if not isinstance(data_sources, list):
                errors.append("data_sources must be an array")
            elif len(data_sources) != 3:
                warnings.append(f"Expected 3 data sources, found {len(data_sources)}")
        
        # Validate total counts
        if "total_candidates" in metadata:
            expected_total = len(self.data.get("unified_pipeline", []))
            actual_total = metadata["total_candidates"]
            if expected_total != actual_total:
                errors.append(f"Metadata total_candidates ({actual_total}) doesn't match unified_pipeline length ({expected_total})")
        
        self.validation_results["validation_checks"]["metadata"] = {
            "status": "PASS" if not errors else "FAIL",
            "errors": errors,
            "warnings": warnings
        }
        
        if errors:
            self.validation_results["errors"].extend(errors)
        if warnings:
            self.validation_results["warnings"].extend(warnings)
    
    def validate_candidate_records(self):
        """Validate individual candidate records"""
        candidates = self.data.get("unified_pipeline", [])
        required_fields = [
            "candidate_id", "company", "company_code", "compound_name",
            "indication", "therapeutic_area", "development_phase", 
            "compound_type", "status"
        ]
        
        valid_companies = ["Novo Nordisk", "Pfizer", "Novartis"]
        valid_company_codes = ["NVO", "PFE", "NVS"]
        valid_phases = ["Phase 1", "Phase 2", "Phase 3", "Registration/Filed"]
        valid_statuses = ["Current", "Discontinued", "Advanced"]
        
        errors = []
        warnings = []
        candidate_ids = set()
        
        for i, candidate in enumerate(candidates):
            record_errors = []
            
            # Check required fields
            for field in required_fields:
                if field not in candidate:
                    record_errors.append(f"Missing required field: {field}")
                elif candidate[field] is None or candidate[field] == "":
                    if field in ["compound_name", "indication", "therapeutic_area"]:
                        record_errors.append(f"Empty value for critical field: {field}")
            
            # Validate candidate_id uniqueness
            if "candidate_id" in candidate:
                cid = candidate["candidate_id"]
                if cid in candidate_ids:
                    record_errors.append(f"Duplicate candidate_id: {cid}")
                else:
                    candidate_ids.add(cid)
                
                # Validate candidate_id format
                if not re.match(r'^(NVO|PFE|NVS)_\d{3}$', cid):
                    record_errors.append(f"Invalid candidate_id format: {cid}")
            
            # Validate controlled vocabulary fields
            if candidate.get("company") not in valid_companies:
                record_errors.append(f"Invalid company: {candidate.get('company')}")
            
            if candidate.get("company_code") not in valid_company_codes:
                record_errors.append(f"Invalid company_code: {candidate.get('company_code')}")
            
            if candidate.get("development_phase") not in valid_phases:
                record_errors.append(f"Invalid development_phase: {candidate.get('development_phase')}")
            
            if candidate.get("status") not in valid_statuses:
                warnings.append(f"Unusual status value: {candidate.get('status')} for {candidate.get('candidate_id')}")
            
            # Validate company code consistency
            if "candidate_id" in candidate and "company_code" in candidate:
                expected_code = candidate["candidate_id"][:3]
                actual_code = candidate["company_code"]
                if expected_code != actual_code:
                    record_errors.append(f"Company code mismatch in candidate_id vs company_code")
            
            if record_errors:
                errors.extend([f"Record {i+1} ({candidate.get('candidate_id', 'UNKNOWN')}): {error}" for error in record_errors])
        
        self.validation_results["validation_checks"]["candidate_records"] = {
            "status": "PASS" if not errors else "FAIL",
            "total_records": len(candidates),
            "unique_candidate_ids": len(candidate_ids),
            "errors": errors[:20],  # Limit to first 20 errors
            "warnings": warnings[:10]  # Limit to first 10 warnings
        }
        
        if errors:
            self.validation_results["errors"].extend(errors[:20])
        if warnings:
            self.validation_results["warnings"].extend(warnings[:10])
    
    def validate_data_consistency(self):
        """Validate data consistency across sections"""
        candidates = self.data.get("unified_pipeline", [])
        companies_section = self.data.get("companies", [])
        summary_stats = self.data.get("summary_statistics", {})
        
        errors = []
        warnings = []
        
        # Count candidates by company
        candidate_counts = Counter(c.get("company") for c in candidates)
        
        # Validate against companies section
        for company_info in companies_section:
            company_name = company_info.get("company_name")
            expected_count = company_info.get("total_candidates", 0)
            actual_count = candidate_counts.get(company_name, 0)
            
            if expected_count != actual_count:
                errors.append(f"Company {company_name}: expected {expected_count} candidates, found {actual_count}")
        
        # Validate against summary statistics
        if "by_company" in summary_stats:
            for company, expected_count in summary_stats["by_company"].items():
                actual_count = candidate_counts.get(company, 0)
                if expected_count != actual_count:
                    errors.append(f"Summary stats mismatch for {company}: expected {expected_count}, found {actual_count}")
        
        # Validate phase distribution
        phase_counts = Counter(c.get("development_phase") for c in candidates)
        if "by_phase" in summary_stats:
            for phase, expected_count in summary_stats["by_phase"].items():
                actual_count = phase_counts.get(phase, 0)
                if expected_count != actual_count:
                    errors.append(f"Phase distribution mismatch for {phase}: expected {expected_count}, found {actual_count}")
        
        # Validate therapeutic area lists
        actual_areas = set(c.get("therapeutic_area") for c in candidates if c.get("therapeutic_area"))
        listed_areas = set(self.data.get("therapeutic_areas", []))
        
        missing_areas = actual_areas - listed_areas
        if missing_areas:
            warnings.append(f"Therapeutic areas in candidates but not in master list: {missing_areas}")
        
        unused_areas = listed_areas - actual_areas
        if unused_areas:
            warnings.append(f"Therapeutic areas in master list but not used: {unused_areas}")
        
        self.validation_results["validation_checks"]["data_consistency"] = {
            "status": "PASS" if not errors else "FAIL",
            "errors": errors,
            "warnings": warnings
        }
        
        if errors:
            self.validation_results["errors"].extend(errors)
        if warnings:
            self.validation_results["warnings"].extend(warnings)
    
    def generate_data_profile(self):
        """Generate data profiling statistics"""
        candidates = self.data.get("unified_pipeline", [])
        
        profile = {
            "total_records": len(candidates),
            "field_completeness": {},
            "value_distributions": {},
            "data_quality_score": 0
        }
        
        # Calculate field completeness
        fields_to_check = [
            "compound_name", "compound_code", "brand_name", "indication",
            "therapeutic_area", "development_phase", "compound_type",
            "mechanism_of_action", "submission_type", "filing_date"
        ]
        
        for field in fields_to_check:
            non_null_count = sum(1 for c in candidates if c.get(field) and c.get(field) != "")
            completeness = (non_null_count / len(candidates)) * 100 if candidates else 0
            profile["field_completeness"][field] = {
                "count": non_null_count,
                "percentage": round(completeness, 1)
            }
        
        # Value distributions
        profile["value_distributions"] = {
            "by_company": dict(Counter(c.get("company") for c in candidates)),
            "by_phase": dict(Counter(c.get("development_phase") for c in candidates)),
            "by_therapeutic_area": dict(Counter(c.get("therapeutic_area") for c in candidates)),
            "by_compound_type": dict(Counter(c.get("compound_type") for c in candidates))
        }
        
        # Calculate data quality score (0-100)
        critical_fields = ["compound_name", "indication", "therapeutic_area", "development_phase"]
        critical_completeness = sum(profile["field_completeness"][f]["percentage"] for f in critical_fields) / len(critical_fields)
        
        error_penalty = min(len(self.validation_results["errors"]) * 5, 50)  # Max 50 point penalty
        warning_penalty = min(len(self.validation_results["warnings"]) * 2, 20)  # Max 20 point penalty
        
        profile["data_quality_score"] = max(0, critical_completeness - error_penalty - warning_penalty)
        
        self.validation_results["summary"] = profile
    
    def run_full_validation(self):
        """Run complete validation suite"""
        print("Starting data validation...")
        
        if not self.load_data():
            self.validation_results["overall_status"] = "FAILED_TO_LOAD"
            return self.validation_results
        
        self.validation_results["total_candidates"] = len(self.data.get("unified_pipeline", []))
        
        # Run validation checks
        print("Validating schema structure...")
        self.validate_schema_structure()
        
        print("Validating metadata...")
        self.validate_metadata()
        
        print("Validating candidate records...")
        self.validate_candidate_records()
        
        print("Validating data consistency...")
        self.validate_data_consistency()
        
        print("Generating data profile...")
        self.generate_data_profile()
        
        # Determine overall status
        has_errors = len(self.validation_results["errors"]) > 0
        self.validation_results["overall_status"] = "FAIL" if has_errors else "PASS"
        
        return self.validation_results
    
    def print_validation_report(self):
        """Print formatted validation report"""
        results = self.validation_results
        
        print("\n" + "="*70)
        print("DATA VALIDATION REPORT")
        print("="*70)
        print(f"Overall Status: {results['overall_status']}")
        print(f"Total Candidates: {results['total_candidates']}")
        print(f"Data Quality Score: {results['summary'].get('data_quality_score', 0):.1f}/100")
        
        print(f"\nValidation Checks:")
        for check_name, check_result in results["validation_checks"].items():
            status = check_result.get("status", "UNKNOWN")
            print(f"  {check_name}: {status}")
        
        if results["errors"]:
            print(f"\nErrors ({len(results['errors'])}):")
            for error in results["errors"][:10]:  # Show first 10
                print(f"  ✗ {error}")
            if len(results["errors"]) > 10:
                print(f"  ... and {len(results['errors']) - 10} more errors")
        
        if results["warnings"]:
            print(f"\nWarnings ({len(results['warnings'])}):")
            for warning in results["warnings"][:5]:  # Show first 5
                print(f"  ⚠ {warning}")
            if len(results["warnings"]) > 5:
                print(f"  ... and {len(results['warnings']) - 5} more warnings")
        
        # Data profile summary
        profile = results["summary"]
        print(f"\nData Completeness:")
        for field, stats in profile.get("field_completeness", {}).items():
            print(f"  {field}: {stats['percentage']}% ({stats['count']}/{results['total_candidates']})")
        
        print(f"\nDistribution Summary:")
        for dist_name, dist_data in profile.get("value_distributions", {}).items():
            print(f"  {dist_name}: {len(dist_data)} unique values")
    
    def save_validation_report(self, output_file="validation_report.json"):
        """Save validation results to JSON file"""
        output_path = self.data_file.parent / output_file
        
        with open(output_path, 'w') as f:
            json.dump(self.validation_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Validation report saved to: {output_path}")

def main():
    """Main function to run validation"""
    # Set data file path
    data_file = Path(__file__).parent / "harmonized_pipeline_data.json"
    
    # Create validator instance
    validator = PipelineDataValidator(data_file)
    
    # Run validation
    results = validator.run_full_validation()
    
    # Print report
    validator.print_validation_report()
    
    # Save report
    validator.save_validation_report()
    
    # Return exit code based on validation status
    return 0 if results["overall_status"] == "PASS" else 1

if __name__ == "__main__":
    exit(main())
