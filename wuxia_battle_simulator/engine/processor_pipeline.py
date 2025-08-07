from typing import List, Optional
from .step_processor import StepProcessor
from .battle_context import BattleContext
from .processors import (
    ATBProcessor,
    AIDecisionProcessor,
    ResourceValidationProcessor,
    MovementSkillProcessor,
    DefenseSkillProcessor,
    DamageCalculationProcessor,
    StateUpdateProcessor,
    EventGenerationProcessor
)


class ProcessorPipeline:
    """
    Orchestrates the execution of battle step processors in the correct order.
    Manages the flow of data through the processing pipeline and handles errors.
    """
    
    def __init__(self):
        self.processors: List[StepProcessor] = []
        self._setup_default_pipeline()
    
    def _setup_default_pipeline(self) -> None:
        """Setup the default processor pipeline in execution order"""
        self.processors = [
            ATBProcessor(),
            AIDecisionProcessor(),
            ResourceValidationProcessor(),
            MovementSkillProcessor(),
            DefenseSkillProcessor(),
            DamageCalculationProcessor(),
            StateUpdateProcessor(),
            EventGenerationProcessor()
        ]
    
    def add_processor(self, processor: StepProcessor, position: Optional[int] = None) -> None:
        """Add a processor to the pipeline at the specified position"""
        if position is None:
            self.processors.append(processor)
        else:
            self.processors.insert(position, processor)
    
    def remove_processor(self, processor_name: str) -> bool:
        """Remove a processor by name from the pipeline"""
        for i, processor in enumerate(self.processors):
            if processor.name == processor_name:
                del self.processors[i]
                return True
        return False
    
    def get_processor(self, processor_name: str) -> Optional[StepProcessor]:
        """Get a processor by name"""
        for processor in self.processors:
            if processor.name == processor_name:
                return processor
        return None
    
    def execute_step(self, context: BattleContext) -> bool:
        """
        Execute a complete battle step through the processor pipeline.
        
        Args:
            context: The battle context containing all state and data
            
        Returns:
            bool: True if step completed successfully, False if aborted
        """
        context.log(f"Starting processor pipeline with {len(self.processors)} processors")
        
        for i, processor in enumerate(self.processors):
            try:
                # Check if we should skip remaining processors
                if context.skip_remaining_processors:
                    context.log(f"Skipping remaining processors from {processor.name} onwards")
                    break
                
                # Check if processor should run
                if not processor.can_process(context):
                    context.log(f"Skipping {processor.name} - conditions not met")
                    continue
                
                context.log(f"Executing processor {i+1}/{len(self.processors)}: {processor.name}")
                
                # Execute the processor
                processor.process(context)
                
                # Check for errors
                if context.has_error():
                    error_msg = f"Error in {processor.name}: {context.error_message}"
                    context.log(error_msg)
                    
                    # Handle the error
                    try:
                        processor.handle_error(context)
                    except Exception as handle_error:
                        context.log(f"Error handler failed for {processor.name}: {str(handle_error)}")
                    
                    # If it's a critical processor, abort the step
                    if processor.critical:
                        context.log(f"Critical processor {processor.name} failed - aborting step")
                        return False
                    
                    # Clear error for non-critical processors
                    context.clear_error()
                
                context.log(f"Completed {processor.name}")
                
            except Exception as e:
                error_msg = f"Unexpected error in {processor.name}: {str(e)}"
                context.log(error_msg)
                context.set_error(error_msg)
                
                # Try to handle the error
                try:
                    processor.handle_error(context)
                except Exception:
                    pass  # Error handler failed, continue
                
                # If it's a critical processor, abort
                if processor.critical:
                    context.log(f"Critical processor {processor.name} crashed - aborting step")
                    return False
                
                # Clear error and continue for non-critical processors
                context.clear_error()
        
        context.log("Processor pipeline completed successfully")
        return True
    
    def get_pipeline_info(self) -> dict:
        """Get information about the current pipeline configuration"""
        return {
            "processor_count": len(self.processors),
            "processors": [
                {
                    "name": p.name,
                    "critical": p.critical,
                    "type": type(p).__name__
                }
                for p in self.processors
            ]
        }
    
    def validate_pipeline(self) -> List[str]:
        """Validate the pipeline configuration and return any issues"""
        issues = []
        
        # Check for duplicate processor names
        names = [p.name for p in self.processors]
        duplicates = set([name for name in names if names.count(name) > 1])
        if duplicates:
            issues.append(f"Duplicate processor names: {duplicates}")
        
        # Check for required processors
        required_types = {
            "ATBProcessor", "AIDecisionProcessor", "DamageCalculationProcessor",
            "StateUpdateProcessor", "EventGenerationProcessor"
        }
        
        present_types = {type(p).__name__ for p in self.processors}
        missing = required_types - present_types
        if missing:
            issues.append(f"Missing required processors: {missing}")
        
        return issues