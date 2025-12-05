#!/usr/bin/env python3
"""
Database Setup Verification Script

Verifies that the Conversation Quality Management database is properly configured.
Run this after setting up the database and running migrations.

Usage:
    python scripts/verify_database_setup.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.database import (
    check_db_connection,
    check_pgvector_extension,
    get_db_context,
)
from app.models import (
    Conversation,
    Message,
    MessageEmbedding,
    ConversationQuality,
    Contradiction,
    ConversationLoop,
    MessageCitation,
)
from sqlalchemy import inspect, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Colors:
    """Terminal colors for output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_success(message: str):
    """Print success message in green"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message: str):
    """Print error message in red"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_warning(message: str):
    """Print warning message in yellow"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


def print_header(message: str):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def verify_database_connection() -> bool:
    """Verify database connection"""
    print_header("1. Database Connection")

    if check_db_connection():
        print_success("Database connection successful")
        return True
    else:
        print_error("Database connection failed")
        print_warning("Check your DATABASE_URL in .env file")
        return False


def verify_pgvector_extension() -> bool:
    """Verify pgvector extension"""
    print_header("2. pgvector Extension")

    if check_pgvector_extension():
        print_success("pgvector extension is installed and available")
        return True
    else:
        print_warning("pgvector extension not available")
        print_warning("Vector similarity search will not work")
        print_warning("Use PostgreSQL with pgvector for full functionality")
        return True  # Don't fail, just warn


def verify_tables() -> bool:
    """Verify all required tables exist"""
    print_header("3. Database Tables")

    expected_tables = {
        'conversations',
        'messages',
        'message_embeddings',
        'conversation_quality',
        'contradictions',
        'conversation_loops',
        'message_citations',
    }

    try:
        with get_db_context() as db:
            inspector = inspect(db.bind)
            existing_tables = set(inspector.get_table_names())

            missing_tables = expected_tables - existing_tables
            extra_tables = existing_tables - expected_tables

            if missing_tables:
                print_error(f"Missing tables: {', '.join(missing_tables)}")
                print_warning("Run: alembic upgrade head")
                return False

            print_success(f"All {len(expected_tables)} required tables exist")

            if extra_tables:
                print(f"  Additional tables found: {', '.join(list(extra_tables)[:5])}")

            return True

    except Exception as e:
        print_error(f"Error checking tables: {e}")
        return False


def verify_indexes() -> bool:
    """Verify critical indexes exist"""
    print_header("4. Database Indexes")

    critical_indexes = [
        ('conversations', 'idx_conversations_user_created'),
        ('messages', 'idx_messages_conversation_sequence'),
        ('message_embeddings', 'idx_embeddings_message'),
        ('contradictions', 'idx_contradictions_conversation'),
        ('conversation_loops', 'idx_loops_conversation'),
    ]

    try:
        with get_db_context() as db:
            inspector = inspect(db.bind)
            missing_indexes = []

            for table_name, index_name in critical_indexes:
                indexes = inspector.get_indexes(table_name)
                index_names = [idx['name'] for idx in indexes]

                if index_name not in index_names:
                    missing_indexes.append((table_name, index_name))

            if missing_indexes:
                print_error(f"Missing {len(missing_indexes)} critical indexes:")
                for table, index in missing_indexes:
                    print(f"  - {index} on {table}")
                return False

            print_success(f"All {len(critical_indexes)} critical indexes exist")

            # Check for HNSW index (pgvector)
            try:
                result = db.execute(text("""
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = 'message_embeddings'
                    AND indexname LIKE '%hnsw%'
                """))
                if result.fetchone():
                    print_success("HNSW vector index exists (for similarity search)")
                else:
                    print_warning("HNSW vector index not found")
            except:
                pass  # Not PostgreSQL or other error

            return True

    except Exception as e:
        print_error(f"Error checking indexes: {e}")
        return False


def verify_constraints() -> bool:
    """Verify key constraints exist"""
    print_header("5. Database Constraints")

    try:
        with get_db_context() as db:
            inspector = inspect(db.bind)

            # Check foreign keys
            fk_tables = ['messages', 'message_embeddings', 'contradictions', 'conversation_loops']
            total_fks = 0

            for table in fk_tables:
                fks = inspector.get_foreign_keys(table)
                total_fks += len(fks)

            if total_fks > 0:
                print_success(f"Found {total_fks} foreign key constraints")
            else:
                print_error("No foreign key constraints found")
                return False

            # Check check constraints (if supported)
            try:
                check_constraints = inspector.get_check_constraints('conversations')
                if len(check_constraints) > 0:
                    print_success(f"Check constraints exist (e.g., health score ranges)")
            except:
                pass  # Not all databases support this

            return True

    except Exception as e:
        print_error(f"Error checking constraints: {e}")
        return False


def verify_model_imports() -> bool:
    """Verify all models can be imported"""
    print_header("6. Model Imports")

    models = [
        ('Conversation', Conversation),
        ('Message', Message),
        ('MessageEmbedding', MessageEmbedding),
        ('ConversationQuality', ConversationQuality),
        ('Contradiction', Contradiction),
        ('ConversationLoop', ConversationLoop),
        ('MessageCitation', MessageCitation),
    ]

    try:
        for name, model in models:
            # Check if model has proper table name
            if hasattr(model, '__tablename__'):
                print_success(f"Model '{name}' imported successfully")
            else:
                print_error(f"Model '{name}' has no __tablename__")
                return False

        return True

    except Exception as e:
        print_error(f"Error importing models: {e}")
        return False


def test_basic_operations() -> bool:
    """Test basic CRUD operations"""
    print_header("7. Basic Operations Test")

    try:
        with get_db_context() as db:
            # Create test conversation
            test_conv = Conversation(
                title="Test Conversation",
                topic="Database verification",
                current_health_score=100.0
            )
            db.add(test_conv)
            db.flush()

            print_success("Created test conversation")

            # Query it back
            retrieved = db.query(Conversation).filter_by(id=test_conv.id).first()
            if retrieved:
                print_success("Retrieved test conversation")
            else:
                print_error("Failed to retrieve test conversation")
                return False

            # Clean up
            db.delete(retrieved)
            db.commit()
            print_success("Deleted test conversation (cleanup)")

            return True

    except Exception as e:
        print_error(f"Error in basic operations test: {e}")
        return False


def print_summary(results: dict):
    """Print verification summary"""
    print_header("Verification Summary")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    print(f"Total checks: {total}")
    print(f"{Colors.GREEN}Passed: {passed}{Colors.END}")
    if failed > 0:
        print(f"{Colors.RED}Failed: {failed}{Colors.END}")
    else:
        print(f"Failed: {failed}")

    print()

    if failed == 0:
        print_success("All verification checks passed!")
        print()
        print(f"{Colors.BOLD}Database is ready for use.{Colors.END}")
        print()
        print("Next steps:")
        print("  1. Implement service layer (quality analysis, contradiction detection)")
        print("  2. Create API routes for quality management")
        print("  3. Set up background workers for embedding generation")
        print("  4. Integrate with frontend for real-time health tracking")
    else:
        print_error("Some verification checks failed")
        print()
        print("Failed checks:")
        for check, passed in results.items():
            if not passed:
                print(f"  - {check}")
        print()
        print("Please fix the issues and run verification again.")

    print()


def main():
    """Run all verification checks"""
    print(f"\n{Colors.BOLD}Conversation Quality Management System{Colors.END}")
    print(f"{Colors.BOLD}Database Setup Verification{Colors.END}\n")

    results = {
        'Database Connection': verify_database_connection(),
        'pgvector Extension': verify_pgvector_extension(),
        'Database Tables': verify_tables(),
        'Database Indexes': verify_indexes(),
        'Database Constraints': verify_constraints(),
        'Model Imports': verify_model_imports(),
        'Basic Operations': test_basic_operations(),
    }

    print_summary(results)

    # Exit with error code if any check failed
    if not all(results.values()):
        sys.exit(1)


if __name__ == '__main__':
    main()
