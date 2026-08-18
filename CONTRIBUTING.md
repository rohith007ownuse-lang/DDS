# Contributing to Driver Drowsiness Detection System

Thank you for your interest in contributing! Here's how you can help.

## Code of Conduct

Be respectful and constructive. We're building together.

## How to Contribute

### 1. Report Issues

Found a bug? Have a feature request?
- Check existing [Issues](https://github.com/yourusername/DriverDrowsinessDetectionSystem/issues)
- Create new issue with:
  - Clear title and description
  - Steps to reproduce (for bugs)
  - Expected vs actual behavior
  - System info (OS, Python version, GPU)

### 2. Submit Code

1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Make changes with clear commits
4. Add tests if applicable
5. Submit pull request with description

### Development Setup

```bash
git clone https://github.com/yourusername/DriverDrowsinessDetectionSystem.git
cd DriverDrowsinessDetectionSystem
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

### Code Style

- **Format**: Follow PEP 8
- **Tool**: Use `black` for formatting
  ```bash
  black src/
  ```
- **Linting**: Use `flake8`
  ```bash
  flake8 src/ --max-line-length=100
  ```
- **Type hints**: Use type annotations
  ```python
  def process_frame(frame: np.ndarray) -> bool:
      pass
  ```

### Testing

- Write tests for new features
- Run tests before submitting PR:
  ```bash
  pytest tests/ -v
  ```
- Aim for >80% code coverage

### Documentation

- Update README for user-facing changes
- Add docstrings to functions:
  ```python
  def detect_face(frame):
      """
      Detect face in frame.
      
      Args:
          frame: Input image array
          
      Returns:
          Face landmarks and bounding box
      """
  ```
- Update architecture docs if structure changes

### Commit Messages

- Use clear, descriptive messages
- Start with verb: "Add", "Fix", "Improve", "Refactor"
- Examples:
  - `Add eye detection module`
  - `Fix PERCLOS calculation accuracy`
  - `Improve performance by 10%`

### Pull Request Process

1. Update documentation
2. Add tests
3. Run code quality checks:
   ```bash
   black src/
   flake8 src/
   pytest tests/
   ```
4. Submit PR with clear description
5. Respond to review feedback

## Architecture Guidelines

### Adding a New Detector

1. Create module in `src/detectors/`
2. Inherit from base detector class
3. Implement `detect()` method
4. Add to fatigue engine integration
5. Write tests in `tests/`
6. Document in `docs/ARCHITECTURE.md`

### Improving Fatigue Engine

- Update weights carefully
- Document changes in comments
- Benchmark against test dataset
- Include before/after accuracy metrics

### UI Changes

- Maintain responsive design
- Test at different resolutions
- Keep accessibility in mind
- Update corresponding docs

## Areas for Contribution

- **Performance**: Optimize detection speed
- **Accuracy**: Improve detection algorithms
- **Features**: Add gaze tracking, expression detection
- **Integration**: Vehicle OBD-II, GPS data
- **Documentation**: Improve guides and examples
- **Tests**: Expand test coverage
- **Bug fixes**: Address issues

## Checklist Before Submitting PR

- [ ] Code follows PEP 8
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No hardcoded values (use config)
- [ ] Meaningful commit messages
- [ ] Tests pass locally
- [ ] No large files added

## Questions?

- Check [Documentation](../docs/)
- Review existing [Issues](https://github.com/yourusername/DriverDrowsinessDetectionSystem/issues)
- Ask in new issue with [Question] tag

## Recognition

Contributors will be:
- Listed in README Contributors section
- Credited in release notes
- Thanked sincerely!

Thank you for helping make this project better! 🙏
